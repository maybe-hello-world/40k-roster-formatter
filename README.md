# 40k-roster-formatter
Just 40 001st way to format your Warhammer 40 000 BattleScribe rosters.  
Current website: https://www.40001format.xyz/

## API usage
Q: Wait, there's an API?!  
A: Always has been! /astronaut-meme.jpg/  

You can download the Postman and import the collection file
from here ([docs/40001format.xyz.postman_collection.json](docs/40001format.xyz.postman_collection.json))
to explore the API. 

Or do it by hand, if you're a masochist.  
```bash
curl --location 'https://www.40001format.xyz/api/formatter' \
--form 'formats="default"' `# default/wtc/rus` \
--form 'hide_basic_selections="on"' `# on/off` \
--form 'show_secondaries="on"' `# on/off` \
--form 'roster=@"/home/user/BattleScribe/rosters/SCARAAAAABS.rosz"' `# roster file` \
--form 'remove_costs="on"' `# on/off` \
--form 'show_model_count="on"'  `# on/off`
```