import json
from generate_clockwise import make,H
specs=[(35,17,93,8,18),(35,17,109,8,18),(43,17,93,8,20)]
cases=[make(rad,lane,span,private=True,exit_extension=ext,bridge_half=half) for rad,lane,span,ext,half in specs]
(H/'order-cases.json').write_text(json.dumps(cases));print([c['id'] for c in cases])
