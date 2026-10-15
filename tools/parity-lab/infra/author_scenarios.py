#!/usr/bin/env python3
"""Reproduce the authored schema-v1 command-state catalog (no server access)."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CLEAR='fill 0 60 0 8 75 8 minecraft:air'
SEL='@e[type=minecraft:marker,tag=pp,x=-32,y=48,z=-32,dx=64,dy=48,dz=64]'
ONE=SEL[:-1]+',limit=1]'
CASES=[]

def case(id,title,category,description,commands,probes,setup=(),cleanup=(),notes=''):
    steps=[{'command':c} if isinstance(c,str) else c for c in commands]
    steps += [{'command':c,'observe':True,'expect_contains':'Test passed'} for c in probes]
    value={'schema_version':1,'id':id,'title':title,'category':category,
           'description':description,'tags':['command','deterministic','state-observation'],
           'setup':['tick freeze',CLEAR,*setup],'steps':steps,'cleanup':[*cleanup,CLEAR,'tick unfreeze'],
           'notes':('Provisioning requests arena force-loading; Pumpkin readiness limitations remain visible. Simulation is frozen for immediate command-state assertions and unfrozen in cleanup; no client or elapsed-tick claim. '
                    'Positive execute predicates return Test passed on vanilla 26.3; errors and empty output fail expectations. '+notes)}
    CASES.append(value)

case('stone-placement','Place a solid block','blocks','A setblock mutation must be visible to a subsequent world-state predicate.',
     ['setblock 2 64 2 minecraft:stone'],['execute if block 2 64 2 minecraft:stone'])
case('replace-existing','Replace an occupied block','blocks','Replacing dirt with gold changes material and removes the old material.',
     ['setblock 2 64 2 minecraft:dirt','setblock 2 64 2 minecraft:gold_block replace'],
     ['execute if block 2 64 2 minecraft:gold_block unless block 2 64 2 minecraft:dirt'])
case('keep-occupied','Keep mode preserves occupied cells','blocks','Keep must leave an occupied stone cell intact even when asked to place gold.',
     [],
     ['execute if block 2 64 2 minecraft:stone unless block 2 64 2 minecraft:gold_block'],
     setup=['setblock 2 64 2 minecraft:stone','setblock 2 64 2 minecraft:gold_block keep'],notes='The keep mutation intentionally reports failure; its state preservation is the observation.')
case('keep-empty','Keep mode fills empty cells','blocks','Keep must place a block when the destination is air.',
     ['setblock 2 64 2 minecraft:gold_block keep'],['execute if block 2 64 2 minecraft:gold_block'])
case('log-axis','Preserve explicit log axis','block-states','A horizontal log retains axis z and fails the incompatible axis predicate.',
     ['setblock 2 64 2 minecraft:oak_log[axis=z]'],
     ['execute if block 2 64 2 minecraft:oak_log[axis=z] unless block 2 64 2 minecraft:oak_log[axis=y]'])
case('stairs-orientation','Preserve stair orientation','block-states','An isolated upper east-facing stair retains facing, half and shape together.',
     ['setblock 2 64 2 minecraft:oak_stairs[facing=east,half=top,shape=straight,waterlogged=false]'],
     ['execute if block 2 64 2 minecraft:oak_stairs[facing=east,half=top,shape=straight,waterlogged=false]'])
case('slab-waterlogged','Preserve waterlogged slab state','block-states','A top slab can carry water while remaining a top slab.',
     ['setblock 2 64 2 minecraft:oak_slab[type=top,waterlogged=true]'],
     ['execute if block 2 64 2 minecraft:oak_slab[type=top,waterlogged=true]'])
case('rotated-pillar-replacement','Replace state on same block type','block-states','Changing a pillar from axis x to z must replace state even without changing its material.',
     ['setblock 2 64 2 minecraft:quartz_pillar[axis=x]','setblock 2 64 2 minecraft:quartz_pillar[axis=z]'],
     ['execute if block 2 64 2 minecraft:quartz_pillar[axis=z] unless block 2 64 2 minecraft:quartz_pillar[axis=x]'])
case('fill-solid-bounds','Fill a bounded solid cuboid','fill','Fill includes both endpoint cells and the center, leaving the adjacent outside cell empty.',
     ['fill 0 64 0 2 66 2 minecraft:stone'],
     ['execute if block 0 64 0 minecraft:stone if block 1 65 1 minecraft:stone if block 2 66 2 minecraft:stone if block 3 65 1 minecraft:air'])
case('fill-material-filter','Replace only matching material','fill','Filtered fill converts stone while leaving a gold exception unchanged.',
     ['fill 0 64 0 2 64 2 minecraft:stone','setblock 1 64 1 minecraft:gold_block','fill 0 64 0 2 64 2 minecraft:dirt replace minecraft:stone'],
     ['execute if block 0 64 0 minecraft:dirt if block 1 64 1 minecraft:gold_block if block 2 64 2 minecraft:dirt'])
case('fill-state-filter','Replace only matching block state','fill','An axis-specific replace predicate affects x logs and preserves y logs.',
     ['setblock 0 64 0 minecraft:oak_log[axis=x]','setblock 1 64 0 minecraft:oak_log[axis=y]',
      'fill 0 64 0 1 64 0 minecraft:gold_block replace minecraft:oak_log[axis=x]'],
     ['execute if block 0 64 0 minecraft:gold_block if block 1 64 0 minecraft:oak_log[axis=y]'])
case('fill-hollow','Hollow fill clears the interior','fill','Hollow constructs the shell and replaces an existing interior block with air.',
     ['setblock 1 65 1 minecraft:gold_block','fill 0 64 0 2 66 2 minecraft:stone hollow'],
     ['execute if block 0 65 1 minecraft:stone if block 1 65 1 minecraft:air if block 2 66 2 minecraft:stone'])
case('fill-outline','Outline fill preserves the interior','fill','Outline changes shell cells but preserves a pre-existing gold interior.',
     ['setblock 1 65 1 minecraft:gold_block','fill 0 64 0 2 66 2 minecraft:stone outline'],
     ['execute if block 0 65 1 minecraft:stone if block 1 65 1 minecraft:gold_block if block 2 66 2 minecraft:stone'])
case('fill-keep','Fill keep preserves occupied holes','fill','A keep fill occupies air cells around a gold exception without overwriting it.',
     ['setblock 1 64 1 minecraft:gold_block','fill 0 64 0 2 64 2 minecraft:stone keep'],
     ['execute if block 0 64 0 minecraft:stone if block 1 64 1 minecraft:gold_block if block 2 64 2 minecraft:stone'])
case('clone-replace-air','Clone replace copies air too','clone','Replace copies solid and air cells, erasing destination gold at the air cell while preserving source.',
     ['setblock 0 64 0 minecraft:stone','fill 4 64 0 5 64 0 minecraft:gold_block','clone 0 64 0 1 64 0 4 64 0 replace normal'],
     ['execute if block 0 64 0 minecraft:stone if block 4 64 0 minecraft:stone if block 5 64 0 minecraft:air'])
case('clone-masked','Masked clone ignores air','clone','Masked cloning copies solid cells and keeps the destination under source air.',
     ['setblock 0 64 0 minecraft:stone','fill 4 64 0 5 64 0 minecraft:gold_block','clone 0 64 0 1 64 0 4 64 0 masked normal'],
     ['execute if block 4 64 0 minecraft:stone if block 5 64 0 minecraft:gold_block'])
case('clone-filtered','Filtered clone selects material','clone','Only stone is copied; a dirt source cell must not replace destination gold.',
     ['setblock 0 64 0 minecraft:stone','setblock 1 64 0 minecraft:dirt','fill 4 64 0 5 64 0 minecraft:gold_block',
      'clone 0 64 0 1 64 0 4 64 0 filtered minecraft:stone normal'],
     ['execute if block 4 64 0 minecraft:stone if block 5 64 0 minecraft:gold_block if block 1 64 0 minecraft:dirt'])
case('clone-move','Moving clone clears source','clone','Move transports an oriented pillar and clears the original cells.',
     ['setblock 0 64 0 minecraft:quartz_pillar[axis=x]','clone 0 64 0 1 64 0 4 64 0 replace move'],
     ['execute if block 0 64 0 minecraft:air if block 4 64 0 minecraft:quartz_pillar[axis=x]'])
case('clone-overlap-force','Forced overlap preserves source snapshot','clone','An overlapping clone shifts two different materials without overwriting the second source before reading it.',
     ['setblock 0 64 0 minecraft:stone','setblock 1 64 0 minecraft:gold_block','clone 0 64 0 1 64 0 1 64 0 replace force'],
     ['execute if block 0 64 0 minecraft:stone if block 1 64 0 minecraft:stone if block 2 64 0 minecraft:gold_block'])
case('positioned-relative','Execute positioned changes relative origin','execute','A relative setblock under positioned execution writes at the translated coordinate.',
     ['execute positioned 2 64 2 run setblock ~1 ~ ~-1 minecraft:stone'],
     ['execute if block 3 64 1 minecraft:stone if block 2 64 2 minecraft:air'])

# These exercise predicate grammar and transfer semantics, rather than adding
# mechanic counts by substituting material names in the placement case.
case('predicate-partial-state','Unspecified properties are wildcards','block-predicates',
     'A stair predicate constraining only facing accepts a top stair; a contradictory half rejects it.',
     ['setblock 2 64 2 minecraft:oak_stairs[facing=east,half=top,shape=straight,waterlogged=false]'],
     ['execute if block 2 64 2 minecraft:oak_stairs[facing=east] unless block 2 64 2 minecraft:oak_stairs[half=bottom]'])
case('predicate-block-tag','Block tags match multiple materials','block-predicates',
     'The logs tag accepts oak and birch but rejects a stone control.',
     ['setblock 0 64 0 minecraft:oak_log','setblock 1 64 0 minecraft:birch_log','setblock 2 64 0 minecraft:stone'],
     ['execute if block 0 64 0 #minecraft:logs if block 1 64 0 #minecraft:logs unless block 2 64 0 #minecraft:logs'])
case('predicate-tag-state','Tags can constrain shared block properties','block-predicates',
     'An axis constraint applies across members of the logs tag and excludes a different orientation.',
     ['setblock 0 64 0 minecraft:oak_log[axis=x]','setblock 1 64 0 minecraft:birch_log[axis=x]',
      'setblock 2 64 0 minecraft:oak_log[axis=y]'],
     ['execute if block 0 64 0 #minecraft:logs[axis=x] if block 1 64 0 #minecraft:logs[axis=x] unless block 2 64 0 #minecraft:logs[axis=x]'])
case('predicate-negation','Unless block gates a real mutation','block-predicates',
     'A false unless branch leaves its destination air; a true branch writes a sentinel.',
     ['setblock 0 64 0 minecraft:stone',
      'execute unless block 0 64 0 minecraft:stone run setblock 1 64 0 minecraft:gold_block',
      'execute unless block 0 64 0 minecraft:dirt run setblock 2 64 0 minecraft:gold_block'],
     ['execute if block 0 64 0 minecraft:stone if block 1 64 0 minecraft:air if block 2 64 0 minecraft:gold_block'])
case('block-entity-nbt-placement','Placement applies block entity NBT','block-states',
     'A barrel placed with an item stack retains its slot, item ID and count in block entity storage.',
     ['setblock 2 64 2 minecraft:barrel{Items:[{Slot:0b,id:"minecraft:diamond",count:3}]}'],
     ['execute if block 2 64 2 minecraft:barrel{Items:[{Slot:0b,id:"minecraft:diamond",count:3}]}'])
case('block-entity-replacement-clears-nbt','Replacing a container clears its old data','blocks',
     'Replacing a populated barrel with stone and then an empty barrel must not resurrect its item stack.',
     ['setblock 2 64 2 minecraft:barrel{Items:[{Slot:0b,id:"minecraft:diamond",count:3}]}',
      {'command':'execute if block 2 64 2 minecraft:barrel{Items:[{Slot:0b,id:"minecraft:diamond",count:3}]}','observe':True,'expect_contains':'Test passed'},
      'setblock 2 64 2 minecraft:stone','setblock 2 64 2 minecraft:barrel'],
     ['execute if block 2 64 2 minecraft:barrel unless data block 2 64 2 Items[0]'])
case('fill-reversed-bounds','Fill normalizes reversed endpoints','fill',
     'Reversing all three axes still fills the inclusive cuboid and leaves its neighbor untouched.',
     ['fill 2 66 2 0 64 0 minecraft:stone'],
     ['execute if block 0 64 0 minecraft:stone if block 1 65 1 minecraft:stone if block 2 66 2 minecraft:stone if block 3 65 1 minecraft:air'])
case('fill-tag-filter','Fill replace accepts a block tag','fill',
     'A logs filter replaces two member materials while preserving a nonmember and air.',
     ['setblock 0 64 0 minecraft:oak_log','setblock 1 64 0 minecraft:birch_log','setblock 2 64 0 minecraft:stone',
      'fill 0 64 0 3 64 0 minecraft:gold_block replace #minecraft:logs'],
     ['execute if block 0 64 0 minecraft:gold_block if block 1 64 0 minecraft:gold_block if block 2 64 0 minecraft:stone if block 3 64 0 minecraft:air'])
case('fill-tag-state-filter','Fill filters tags and states together','fill',
     'A shared axis predicate replaces matching log types but preserves another orientation.',
     ['setblock 0 64 0 minecraft:oak_log[axis=x]','setblock 1 64 0 minecraft:birch_log[axis=x]',
      'setblock 2 64 0 minecraft:oak_log[axis=y]','fill 0 64 0 2 64 0 minecraft:gold_block replace #minecraft:logs[axis=x]'],
     ['execute if block 0 64 0 minecraft:gold_block if block 1 64 0 minecraft:gold_block if block 2 64 0 minecraft:oak_log[axis=y]'])
case('clone-state-filter','Clone filters individual block states','clone',
     'A state filter copies one oriented log and preserves destination cells under nonmatching source states.',
     ['setblock 0 64 0 minecraft:oak_log[axis=x]','setblock 1 64 0 minecraft:oak_log[axis=y]',
      'fill 4 64 0 5 64 0 minecraft:gold_block','clone 0 64 0 1 64 0 4 64 0 filtered minecraft:oak_log[axis=x] normal'],
     ['execute if block 0 64 0 minecraft:oak_log[axis=x] if block 1 64 0 minecraft:oak_log[axis=y] if block 4 64 0 minecraft:oak_log[axis=x] if block 5 64 0 minecraft:gold_block'])
case('clone-block-entity-nbt','Clone copies block entity data','clone',
     'Cloning a populated barrel copies its item stack and facing while preserving the original.',
     ['setblock 0 64 0 minecraft:barrel[facing=east]{Items:[{Slot:0b,id:"minecraft:diamond",count:3}]}',
      'clone 0 64 0 0 64 0 4 64 0 replace normal'],
     ['execute if block 0 64 0 minecraft:barrel[facing=east]{Items:[{Slot:0b,id:"minecraft:diamond",count:3}]} if block 4 64 0 minecraft:barrel[facing=east]{Items:[{Slot:0b,id:"minecraft:diamond",count:3}]}'])
case('clone-masked-move','Masked move leaves destination under air','clone',
     'A masked move clears the solid source and preserves gold under source air at the destination.',
     ['setblock 0 64 0 minecraft:stone','fill 4 64 0 5 64 0 minecraft:gold_block',
      'clone 0 64 0 1 64 0 4 64 0 masked move'],
     ['execute if block 0 64 0 minecraft:air if block 1 64 0 minecraft:air if block 4 64 0 minecraft:stone if block 5 64 0 minecraft:gold_block'])
case('clone-overlap-normal-preserves','Normal clone rejects overlap without writes','clone',
     'A rejected overlapping normal clone preserves both distinct source cells and the destination extension.',
     [],['execute if block 0 64 0 minecraft:stone if block 1 64 0 minecraft:gold_block if block 2 64 0 minecraft:air'],
     setup=['setblock 0 64 0 minecraft:stone','setblock 1 64 0 minecraft:gold_block',
            'clone 0 64 0 1 64 0 1 64 0 replace normal'],
     notes='The overlapping mutation intentionally fails in setup; unchanged positive state is the observation.')

def score(id,title,description,commands,predicates):
    case(id,title,'scoreboard',description,commands,
         ['execute '+p for p in predicates],setup=['scoreboard objectives add pp dummy'],
         cleanup=['scoreboard objectives remove pp'])

score('score-add-remove','Score addition and subtraction','Set, add and remove must produce the expected signed score.',
      ['scoreboard players set value pp -4','scoreboard players add value pp 13','scoreboard players remove value pp 2'],['if score value pp matches 7'])
score('score-multiply','Score multiplication','The *= operation changes the destination and preserves the source.',
      ['scoreboard players set a pp -3','scoreboard players set b pp 7','scoreboard players operation a pp *= b pp'],['if score a pp matches -21 if score b pp matches 7'])
score('score-division-floor','Negative score division rounds down','Integer scoreboard division uses floor division for a negative dividend.',
      ['scoreboard players set a pp -7','scoreboard players set b pp 3','scoreboard players operation a pp /= b pp'],['if score a pp matches -3 if score b pp matches 3'])
score('score-modulo','Negative score modulo','Modulo with positive divisor yields a nonnegative remainder for a negative dividend.',
      ['scoreboard players set a pp -7','scoreboard players set b pp 3','scoreboard players operation a pp %= b pp'],['if score a pp matches 2'])
score('score-swap','Swap both score values','The >< operation exchanges destination and source rather than copying.',
      ['scoreboard players set a pp 4','scoreboard players set b pp 9','scoreboard players operation a pp >< b pp'],['if score a pp matches 9 if score b pp matches 4'])
score('score-minimum','Score minimum operation','The < operation selects the smaller value and preserves its source.',
      ['scoreboard players set a pp 12','scoreboard players set b pp -2','scoreboard players operation a pp < b pp'],['if score a pp matches -2 if score b pp matches -2'])
score('score-maximum','Score maximum operation','The > operation selects the larger signed value.',
      ['scoreboard players set a pp -12','scoreboard players set b pp -2','scoreboard players operation a pp > b pp'],['if score a pp matches -2 if score b pp matches -2'])
score('score-assignment','Score assignment preserves source','The = operation copies one score and leaves the original untouched.',
      ['scoreboard players set a pp 1','scoreboard players set b pp 37','scoreboard players operation a pp = b pp'],['if score a pp = b pp if score b pp matches 37'])

def entity(id,title,description,commands,probes,setup=(),cleanup=(),category='entities'):
    case(id,title,category,description,commands,probes,
         setup=[f'execute if entity {SEL} run kill {SEL}',*setup],
         cleanup=[f'execute if entity {SEL} run kill {SEL}',*cleanup],
         notes='Requires marker entities and selectors; missing support remains a visible mismatch. No UUID or entity display-name output is compared.')

def summon(x=2,tag='',data=''):
    tags='["pp"'+(',"'+tag+'"' if tag else '')+']'
    return f'summon minecraft:marker {x} 64 2 {{Tags:{tags}'+(','+data if data else '')+'}'

entity('tag-add-selector','Tag addition changes selection','Adding a tag makes an existing entity match the positive tag predicate.',
       [summon(),f'tag {ONE} add chosen'],[f'execute if entity {ONE[:-1]},tag=chosen]'])
entity('tag-remove-selector','Tag removal changes selection','Removing chosen preserves the entity and makes the negated tag selector match.',
       [summon(tag='chosen'),f'tag {ONE} remove chosen'],[f'execute if entity {ONE[:-1]},tag=!chosen] unless entity {SEL[:-1]},tag=chosen]'])
entity('tag-intersection','Multiple tags intersect selectors','Intersecting chosen and !excluded isolates one entity before adding selected.',
       [summon(tag='chosen'),summon(4,tag='chosen',data='data:{excluded:1b}'),
        f'tag @e[type=minecraft:marker,tag=pp,x=4,y=64,z=2,distance=..0.1,limit=1] add excluded',
        f'tag {SEL[:-1]},tag=chosen,tag=!excluded] add selected'],
       [f'execute if entity {SEL[:-1]},tag=selected,tag=!excluded] unless entity {SEL[:-1]},tag=selected,tag=excluded]'])
entity('entity-nbt-summon','Summon preserves nested entity NBT','Marker custom data supplied in summon must be readable by an NBT predicate.',
       [summon(data='data:{value:7,nested:{flag:1b}}')],
       [f'execute if entity {ONE[:-1]},nbt={{data:{{value:7,nested:{{flag:1b}}}}}}]'],category='entity-nbt')
entity('entity-nbt-merge','Merge preserves sibling NBT','Merging marker data changes one child while keeping the untouched sibling.',
       [summon(data='data:{left:1,right:9}'),f'data merge entity {ONE} {{data:{{left:5}}}}'],
       [f'execute if entity {ONE[:-1]},nbt={{data:{{left:5,right:9}}}}]'],category='entity-nbt')
entity('entity-nbt-list','Append extends an NBT list','Appending to marker data adds the new member while retaining both initial members.',
       [summon(data='data:{values:[2,4]}'),f'data modify entity {ONE} data.values append value 8'],
       [f'execute if data entity {ONE} data.values[0]',f'execute if entity {ONE[:-1]},nbt={{data:{{values:[2,4,8]}}}}]'],category='entity-nbt')
entity('entity-teleport','Teleport mutates stored position','Integer teleport coordinates center x/z on blocks; marker Pos NBT must reflect that centering.',
       [summon(),f'teleport {ONE} 4 65 4'],
       [f'execute if entity {ONE[:-1]},nbt={{Pos:[4.5d,65.0d,4.5d]}}]'])
entity('kill-tag-isolation','Kill affects only the selected tag','Killing the chosen marker leaves an unchosen marker alive.',
       [summon(tag='chosen'),summon(4),f'kill {SEL[:-1]},tag=chosen]'],
       [f'execute if entity {SEL[:-1]},tag=!chosen] unless entity {SEL[:-1]},tag=chosen]'])
entity('selector-score-count','Execute as counts selected entities','Execute as runs once per marker and increments a fake-player score twice.',
       [summon(),summon(4),'scoreboard players set count pp 0',f'execute as {SEL} run scoreboard players add count pp 1'],
       ['execute if score count pp matches 2'],setup=['scoreboard objectives add pp dummy'],cleanup=['scoreboard objectives remove pp'],category='scoreboard')

if __name__=='__main__':
    directory=ROOT/'scenarios';directory.mkdir(exist_ok=True)
    for scenario in CASES:
        (directory/(scenario['id']+'.json')).write_text(json.dumps(scenario,indent=2)+'\n')
    print(f'Authored {len(CASES)} distinct scenarios')
