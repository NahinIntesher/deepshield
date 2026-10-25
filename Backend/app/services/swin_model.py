"""Architecture copied from the supplied training/model.py; no pretrained download by default."""
import math,torch,torch.nn as nn,torch.nn.functional as F,timm

def dct_filters(n=8):
    x=torch.arange(n).float()
    C=torch.cos(math.pi/n*(x[None,:]+.5)*x[:,None])
    C[0]*=1/math.sqrt(n);C[1:]*=math.sqrt(2/n)
    return torch.stack([torch.outer(C[u],C[v]) for u in range(n) for v in range(n)]).unsqueeze(1)

class DCTBranch(nn.Module):
    def __init__(self,d=256):
        super().__init__()
        self.register_buffer("dct",dct_filters())
        self.register_buffer("mean",torch.tensor([.485,.456,.406])[None,:,None,None])
        self.register_buffer("std",torch.tensor([.229,.224,.225])[None,:,None,None])
        self.net=nn.Sequential(
            nn.Conv2d(64,96,3,1,1,bias=False),nn.GroupNorm(8,96),nn.GELU(),
            nn.Conv2d(96,128,3,2,1,bias=False),nn.GroupNorm(8,128),nn.GELU(),
            nn.Conv2d(128,192,3,2,1,bias=False),nn.GroupNorm(8,192),nn.GELU(),
            nn.AdaptiveAvgPool2d(1),nn.Flatten(),nn.Linear(192,d),nn.LayerNorm(d))

    def forward(self,x):
        x=(x*self.std.to(x.dtype)+self.mean.to(x.dtype)).clamp(0,1)
        x=.299*x[:,0:1]+.587*x[:,1:2]+.114*x[:,2:3]
        z=F.conv2d(x,self.dct.to(x.dtype),stride=8).abs().log1p()
        z=(z-z.mean((2,3),keepdim=True))/(z.std((2,3),keepdim=True)+1e-6)
        return self.net(z)

class GatedFusion(nn.Module):
    def __init__(self,d=256):
        super().__init__()
        self.norm=nn.ModuleList([nn.LayerNorm(d) for _ in range(3)])
        self.gate=nn.Sequential(nn.Linear(d*3,d*3),nn.GELU(),
                                nn.Dropout(.1),nn.Linear(d*3,d*3))
        self.d=d

    def forward(self,r,f,t):
        xs=[n(x) for n,x in zip(self.norm,(r,f,t))]
        s=torch.stack(xs,1)
        g=torch.softmax(self.gate(torch.cat(xs,1)).view(-1,3,self.d),1)
        return (s*g).sum(1),g.mean(-1)

class DeepfakeModel(nn.Module):
    def __init__(self,d=256,frames=16,pretrained=False):
        super().__init__();self.stage=1
        self.rgb=timm.create_model("swin_small_patch4_window7_224",
                                   pretrained=pretrained,num_classes=0)
        self.rgb.set_grad_checkpointing(False)
        rd=self.rgb.num_features

        self.rgb_proj=nn.Sequential(nn.Linear(rd,d),nn.LayerNorm(d))
        self.freq=DCTBranch(d)
        self.pos=nn.Parameter(torch.zeros(1,frames,d))

        enc=nn.TransformerEncoderLayer(
            d,4,d*4,.1,activation="gelu",
            batch_first=True,norm_first=True)
        self.temporal=nn.TransformerEncoder(
            enc,2,enable_nested_tensor=False)

        self.fusion=GatedFusion(d)
        self.cls=nn.Sequential(nn.LayerNorm(d),nn.Linear(d,128),
                               nn.GELU(),nn.Dropout(.3),nn.Linear(128,2))
        nn.init.trunc_normal_(self.pos,std=.02)
        self.set_stage(1)

    def set_stage(self,stage):
        self.stage=stage
        for p in self.rgb.parameters():p.requires_grad=False
        if stage==2:
            for layer in self.rgb.layers[-2:]:
                for p in layer.parameters():p.requires_grad=True
            for p in self.rgb.norm.parameters():p.requires_grad=True
        self.rgb.set_grad_checkpointing(False)

    def train(self,mode=True):
        super().train(mode)
        if mode:
            self.rgb.eval()
            if self.stage==2:
                for l in self.rgb.layers[-2:]:l.train()
                self.rgb.norm.train()
        return self

    def forward(self,x,rgb_cache=None,return_aux=False):
        B,T,C,H,W=x.shape;f=x.reshape(B*T,C,H,W)

        if self.stage==1 and rgb_cache is not None:
            raw=rgb_cache.float()
        else:
            if self.stage==1:
                with torch.no_grad():raw=self.rgb(f)
            else:raw=self.rgb(f)
            raw=raw.reshape(B,T,-1)

        r=self.rgb_proj(raw)
        rgb=r.mean(1)
        freq=self.freq(f).reshape(B,T,-1).mean(1)
        temp=self.temporal(r+self.pos[:,:T]).mean(1)
        fused,gates=self.fusion(rgb,freq,temp)
        out=self.cls(fused)

        return (out,{"gates":gates}) if return_aux else out