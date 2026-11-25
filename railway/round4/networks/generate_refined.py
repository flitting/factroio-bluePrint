import json
from generate_clockwise import make,H
specs=[(35,17,61,8,18),(35,17,61,16,18),(43,17,61,8,20),(43,17,61,16,20),(59,17,77,8,32),(75,17,77,8,48)]
cases=[make(rad,lane,span,private=True,exit_extension=ext,bridge_half=half) for rad,lane,span,ext,half in specs]
(H/'refined-cases.json').write_text(json.dumps(cases));print([c['id'] for c in cases])
