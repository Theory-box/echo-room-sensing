# Echo Room Sensing

Experimental: mapping a room with a phone's speakers and microphones (acoustic
echolocation). The goal is a clean room shell (walls, floor and ceiling as planes,
turned into a polygon mesh) plus rough boxes for furniture, from a few static captures.

**This is a test project, not a product or a download.**

See **[STATUS.md](STATUS.md)** for the current findings and options.

## Stages
1. **Echo diagnostic** (`diagnostic/`): checks whether the phone's speakers, mics and
   motion sensors are good enough. Everything runs in the browser; nothing is uploaded.
2. Rotations and direction finding.
3. Solving walls from several spots → room shell mesh.
4. Furniture boxes and rough material tags.
