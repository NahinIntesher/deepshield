export interface ShapGame {
 algorithm:'exact'|'permutation';feature_names:string[];values:number[];
 base_value:number;output_value:number;additivity_error:number;max_evals:number;seed:number|null;
}
export interface ShapRegion {id:'eyes'|'nose'|'mouth'|'other';rectangles:number[][];shap_value:number;masked_class_score_percent:number;score_drop_percentage_points:number;preview?:string}
export interface ShapEvidence {
 version:number;method:'SHAP';library_version:string;target_class:'Real'|'Fake';target:string;units:string;
 reference:{type:string;radius:number;description:string};
 branches:ShapGame;frames:(ShapGame&{source_indices:number[];timestamps:(number|null)[];permutation_cycles:number})|null;
 spatial:ShapGame&{regions:ShapRegion[];coalitions_evaluated:number;preview:{position:number;source_frame:number;timestamp:number|null;original:string}};
 original_class_score_percent:number;reference_class_score_percent:number;seconds:number;limitation:string;
}
