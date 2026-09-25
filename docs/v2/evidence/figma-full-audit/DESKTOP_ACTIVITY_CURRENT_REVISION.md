# Desktop Activity — current Figma revision

Current Figma [Activity `189:1342`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=189-1342) was read directly. Its current example shows one active item and empty Waiting on you and Recently finished cards. Production already renders real jobs, continuations, and finished outcomes from engine state. This increment changed the two empty-card labels to Figma's “All clear.”

An isolated package with no work rendered the [1440px empty state](DESKTOP_ACTIVITY_EMPTY_PACKAGE_1440.png) and [800px empty state](DESKTOP_ACTIVITY_EMPTY_PACKAGE_800.png). At 1440px, the three cards measured x613/y183, x613/y280, and x613/y372, each 670px wide. At 800px they measured x371/y179, x371/y276, and x371/y368, each 388px wide. No overflow or renderer error appeared. The populated active item in Figma was not fabricated or package-verified; real running work remains open.
