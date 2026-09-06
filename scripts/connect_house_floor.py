"""Retain the connected walking floor and remove inaccessible pockets behind furniture."""
import json
from pathlib import Path

def connected_floor(rows):
    height=len(rows);width=len(rows[0]);remaining={(x,z) for z,row in enumerate(rows) for x,value in enumerate(row) if value=='1'}
    largest=set()
    while remaining:
        start=remaining.pop();component={start};queue=[start]
        for x,z in queue:
            for p in [(x+1,z),(x-1,z),(x,z+1),(x,z-1)]:
                if p in remaining:remaining.remove(p);component.add(p);queue.append(p)
        if len(component)>len(largest):largest=component
    return [''.join('1' if (x,z) in largest else '0' for x in range(width)) for z in range(height)]

if __name__=='__main__':
    for path in (Path(__file__).resolve().parents[1]/'static/house').glob('*/navigation.json'):
        data=json.loads(path.read_text());data['rows']=connected_floor(data['rows']);data['connectedFloorOnly']=True
        path.write_text(json.dumps(data,separators=(',',':')))
        print('CONNECTED_FLOOR',path.parent.name,sum(row.count('1') for row in data['rows']))
