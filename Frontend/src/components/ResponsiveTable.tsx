'use client';
import {Children,cloneElement,isValidElement,type HTMLAttributes,type ReactElement,type ReactNode} from 'react';

type Element=ReactElement<{children?:ReactNode;className?:string;role?:string}>;
const elements=(value:ReactNode)=>Children.toArray(value).filter(isValidElement) as Element[];

/** Keep table headers on desktop and repeat their labels in the mobile card layout. */
export function ResponsiveTable({children,className='',...props}:HTMLAttributes<HTMLDivElement>){
 const table=elements(children).find(child=>child.type==='table');
 if(!table)return <div className={`responsive-table ${className}`} {...props}>{children}</div>;
 const head=elements(table.props.children).find(child=>child.type==='thead');
 const headerRow=elements(head?.props.children)[0];
 const headings=elements(headerRow?.props.children).map(cell=>cell.props.children);
 const sections=Children.map(table.props.children,section=>{
  if(!isValidElement(section)||section.type!=='tbody')return section;
  const body=section as Element;
  return cloneElement(body,{role:'rowgroup'},Children.map(body.props.children,row=>{
   if(!isValidElement(row)||row.type!=='tr')return row;
   const tr=row as Element;
   return cloneElement(tr,{role:'row'},Children.map(tr.props.children,(cell,index)=>{
    if(!isValidElement(cell)||cell.type!=='td')return cell;
    const td=cell as Element;
    return cloneElement(td,{role:'cell'},<>{headings[index]&&<span className="mobile-cell-label" aria-hidden="true">{headings[index]}</span>}<div className="mobile-cell-value">{td.props.children}</div></>);
   }));
  }));
 });
 return <div className={`responsive-table ${className}`} {...props}>{cloneElement(table,{role:'table'},sections)}{Children.toArray(children).filter(child=>!isValidElement(child)||child.type!=='table')}</div>;
}
