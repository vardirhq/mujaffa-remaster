# Original showroom runtime assets

The original SWF scene map identifies main-timeline frame 730 (`showroom`) as the canonical garage/showroom composition. Character 934 is the room artwork behind the customizable car root (character 875).

The runtime art preparation step now copies character 934 directly from the lossless SWF vector extraction into `assets/generated/showroom/original-showroom-background.png` and records its original bounds in `assets/generated/showroom/manifest.json`.

The previous invented dark garage environment is removed from the presentation pass. Responsive mobile controls remain temporary interaction scaffolding while the remaining original UI groups are reconstructed from the SWF.
