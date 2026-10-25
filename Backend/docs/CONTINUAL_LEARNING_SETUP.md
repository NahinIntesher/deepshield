# Continual learning setup

The Train button is disabled until preflight checks pass. The error about replay_manifest.json means the memory/evaluation configuration is missing; it does not mean a model candidate has been uploaded incorrectly. A candidate is an output of training, not an input from a participant.

Required inputs:
1. The original trained baseline checkpoint.
2. At least one research contribution that an Admin has reviewed and approved.
3. Old training examples in split `replay`, including verified Real and Fake videos.
4. Separate old examples in `retention` to measure loss of previous ability.
5. Separate new examples in `new_validation` to measure performance on new data.

Each of the last three splits requires both labels. File contents must not cross training and evaluation splits. Use FaceForensics++ training partitions or an appropriately consented collection. Celeb-DF and WildDeepfake remain held out; do not use them as adaptation memory.

Copy `Database/continual/replay_manifest.example.json` to `Database/continual/replay_manifest.json` and replace every example path with a real, independently verified video. Relative paths are resolved from the manifest directory. Example filenames are not real supplied training data; merely copying the example is insufficient.

The Admin screen lists missing requirements and approved sample counts. Full training validation also verifies paths, labels, dataset provenance and content hashes. It trains a separate candidate with replay and distillation, evaluates old/new holdouts, and saves a report and candidate under `Database/continual`. It does not replace or auto-promote the active baseline checkpoint.

The provided eight gameplay clips have not been silently repurposed into disjoint training/evaluation memory. Configure genuine independent examples before starting a training experiment.
