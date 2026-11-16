# Changelog

All notable changes to WIKC are listed here, with the people who made them.

## 2026-11-16

Integrated from [GuGuaTT/WIKC](https://github.com/GuGuaTT/WIKC).

### Added
- Independent web and flange local imperfection amplitudes (`local_scale_web`, `local_scale_flange`, `couple_local`). By Tianyu Gu ([@GuGuaTT](https://github.com/GuGuaTT)).
- In-plane and out-of-plane member out-of-straightness and out-of-plumbness (`straight_scale_ip/op`, `plumb_scale_ip/op`). By Tianyu Gu.
- Half-model support (`is_half_model`). By Tianyu Gu.
- Finite-thickness web-node identification for solid meshes (`local_node_mode=solid`; the default `legacy` keeps the original rule). By Tianyu Gu.
- W14X159 solid–beam example. By Tianyu Gu.

### Changed
- Imperfection options are parsed and validated in the new `pywikc/imperfections/options.py` (explicit Boolean parsing, unknown keys rejected). By Tianyu Gu.
- Input reading handles blank lines and end of definition files more robustly; beam-node coordinates are transformed using the actual Abaqus `*System` definitions. By Tianyu Gu.
- DBBW example and README updated. By Tianyu Gu.
- README note on a possible convergence issue (written 2022-09-27, not previously in the lab repository). By Alex Hartloper ([@ahartloper](https://github.com/ahartloper)).

### Removed
- Committed `__pycache__` files; `__pycache__/` and `*.pyc` are now in `.gitignore`.
