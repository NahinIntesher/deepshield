const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,file);
const {validShap,blurObservation,resultMeaning}=require('../src/lib/explanation.ts');
const folder=path.resolve(__dirname,'../../Backend/docs/review/explanation-audit');
// Public checkouts use numeric synthetic evidence. Local real-video audit files
// are optional and remain private because they contain face previews.
function fixture(verdict){
 const png='data:image/png;base64,iVBORw0KGgo=';
 const game=(feature_names,values)=>({feature_names,values,base_value:0,output_value:values.reduce((a,b)=>a+b,0)});
 const spatial=game(['eyes','nose','mouth','other'],[.4,.3,.2,.1]);
 spatial.preview={original:png};spatial.regions=spatial.feature_names.map((id,i)=>({id,shap_value:spatial.values[i],masked_class_score_percent:70,preview:png}));
 return {verdict,media_type:'video',confidence_percentage:90,shap_explanation:{method:'SHAP',target_class:verdict,branches:game(['rgb','frequency','temporal'],[.5,.3,.2]),spatial}};
}
for(const name of ['real','fake']){
 const audit=path.join(folder,`shap-${name}.json`);
 const result=fs.existsSync(audit)?JSON.parse(fs.readFileSync(audit)):fixture(name==='real'?'Real':'Fake');
 assert.ok(validShap(result));
 const area=result.shap_explanation.spatial.regions.find(r=>r.id==='eyes');
 assert.match(blurObservation(result,area,false),/went from/);
 assert.match(blurObservation(result,area,true),/ঝাপসা করে আবার পরীক্ষা/);
 assert.match(resultMeaning(result,true),name==='fake'?/(হতে|থাকতে) পারে/:/যাচাই করে না/);
 const altered=structuredClone(result);altered.shap_explanation.target_class=name==='real'?'Fake':'Real';assert.equal(validShap(altered),null);
 const bad=structuredClone(result);bad.shap_explanation.spatial.values[0]+=1;assert.equal(validShap(bad),null);
 const missing=structuredClone(result);delete missing.shap_explanation.spatial;assert.equal(validShap(missing),null);
 const mismatch=structuredClone(result);mismatch.shap_explanation.spatial.regions[0].shap_value+=1;assert.equal(validShap(mismatch),null);
 const preview=structuredClone(result);delete preview.shap_explanation.spatial.preview;assert.equal(validShap(preview),null);
}
console.log('Explanation contracts passed for Real/Fake, including mismatched and tampered attribution rejection. Private actual-video audits are used when present.');
