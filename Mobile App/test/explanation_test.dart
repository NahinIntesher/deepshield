import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:deepshield_mobile/core/api.dart';
import 'package:deepshield_mobile/features/model_explanation.dart';

// Synthetic attribution data tests the display contract, not model accuracy.
Json evidence() {
  const png = 'data:image/png;base64,iVBORw0KGgo=';
  Json game(List<String> names, List<double> values) => {
    'feature_names': names,
    'values': values,
    'base_value': 0,
    'output_value': values.fold<double>(0, (sum, value) => sum + value),
  };
  final spatial = game(['eyes', 'nose', 'mouth', 'other'], [.4, .3, .2, .1]);
  spatial['preview'] = {'original': png};
  spatial['regions'] = List.generate(
    4,
    (i) => {
      'id': (spatial['feature_names'] as List)[i],
      'shap_value': (spatial['values'] as List)[i],
      'masked_class_score_percent': 70.0,
      'preview': png,
    },
  );
  return {
    'verdict': 'Fake',
    'shap_explanation': {
      'method': 'SHAP',
      'target_class': 'Fake',
      'branches': game(['rgb', 'dct', 'temporal'], [.5, .3, .2]),
      'spatial': spatial,
    },
  };
}

void main() {
  test('Accepts consistent evidence and gracefully rejects partial data', () {
    expect(verifiedShap(evidence()), isNotNull);
    for (final missing in ['branches', 'spatial']) {
      final data = evidence();
      (data['shap_explanation'] as Map).remove(missing);
      expect(verifiedShap(data), isNull);
    }
    expect(verifiedShap({'verdict': 'Real'}), isNull);
  });
  test('Rejects mismatched classes, duplicate regions and tampered values', () {
    for (final mutation in [
      'class',
      'duplicate',
      'value',
      'preview',
      'score',
      'sum',
    ]) {
      final data = object(jsonDecode(jsonEncode(evidence())));
      final shap = data['shap_explanation'] as Map;
      final spatial = shap['spatial'] as Map;
      final region = (spatial['regions'] as List).first as Map;
      switch (mutation) {
        case 'class':
          shap['target_class'] = 'Real';
        case 'duplicate':
          region['id'] = 'nose';
        case 'value':
          region['shap_value'] = 2;
        case 'preview':
          spatial['preview'] = null;
        case 'score':
          region['masked_class_score_percent'] = 101;
        case 'sum':
          (shap['branches'] as Map)['output_value'] = 5;
      }
      expect(verifiedShap(data), isNull, reason: mutation);
    }
  });
}
