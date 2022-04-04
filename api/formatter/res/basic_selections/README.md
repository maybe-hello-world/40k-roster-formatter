## Basic Selections catalogue
In this folder there are catalogues of basic selections for holders (usually, units).
Each catalogue should provide faction name and list of holders
and basic selections for these holders. These base selections wouldn't be
displayed if "minimize output" option is enabled.

Faction name could be partial. During parsing, engine would try to find
the closest faction match with this holder inside, if no exact match is found,
then it will separate faction name by dashes and remove the last item and try
to match again.

So, for Infiltrators unit of Iron Hands it will try to find their matches in the next order:
- general (general database for all units)
- Imperium - Adeptus Astartes - Iron Hands
- Imperium - Adeptus Astartes
- Imperium

If selection is listed for the unit in any of them, it will be omitted.

Faction file example:
```yaml
---
faction: Imperium - Adeptus Astartes - Iron Hands
selections:
  Unit Name 1:
    - Super Rifle 1
    - Not Super Rifle 2
  
  Unit Name 2:
    - Some Pistol
    - Some Shotgun
 ...
```