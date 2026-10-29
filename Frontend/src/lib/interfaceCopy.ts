import copy from './interface-copy.json';
export const interfaceCopy:Record<string,{en:string;bn:string}>=copy;
export function authoredCopy(en:string,bn:string|undefined,language:string,fallback:(value:string)=>string){
 if(typeof en!=='string')return '';
 const revised=interfaceCopy[en];
 return revised?(language==='bn'?revised.bn:revised.en):language==='bn'?(bn??fallback(en)):en;
}
