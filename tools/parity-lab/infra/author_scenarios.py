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
        f'tag @e[type=minecraft:marker,tag=pp,x=4.5,y=64,z=2.5,distance=..0.1,limit=1] add excluded',
        f'tag {SEL[:-1]},tag=chosen,tag=!excluded] add selected'],
       [f'execute if entity {SEL[:-1]},tag=selected,tag=!excluded] if entity {SEL[:-1]},tag=excluded,tag=!selected] unless entity {SEL[:-1]},tag=selected,tag=excluded]'])
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

# Entity expansion: use tagged fixtures and positive controls, including before
# destructive operations. Each case isolates a different selector/mutation rule.
def select(options='', *, origin=None, kind='minecraft:marker'):
    bounds=origin or 'x=-32,y=48,z=-32,dx=64,dy=48,dz=64'
    return f'@e[type={kind},tag=pp,{bounds}'+(','+options if options else '')+']'

def marked(x=2, *, tag='fixture', data='', y=64, z=2):
    return f'summon minecraft:marker {x} {y} {z} {{Tags:["pp","{tag}"]'+(','+data if data else '')+'}'

def positive(command):
    return {'command':command,'observe':True,'expect_contains':'Test passed'}

entity('entity-summon-position-precedence','Summon coordinates override Pos NBT',
       'Explicit summon coordinates determine position even when the NBT supplies a conflicting Pos.',
       [marked(data='Pos:[9.0d,70.0d,9.0d]')],
       [f'execute if entity {select(origin="x=2.5,y=64,z=2.5,distance=..0.1")} unless entity {select(origin="x=9,y=70,z=9,distance=..0.1")}'])

entity('selector-distance-inclusive','Distance bounds include both endpoints',
       'Markers at distances two and four match 2..4; an exterior marker remains excluded.',
       [marked(2,tag='lower'),marked(4,tag='upper'),marked(5,tag='outside'),
        f'tag {select(origin="x=0.5,y=64,z=2.5,distance=2..4")} add selected'],
       [f'execute if entity {select("tag=lower,tag=selected")} if entity {select("tag=upper,tag=selected")} if entity {select("tag=outside,tag=!selected")}'])

entity('selector-negative-box','Negative box deltas normalize the selection',
       'A box extending back four blocks includes both interior markers while excluding either neighbor.',
       [marked(4,tag='low'),marked(8,tag='high'),marked(3,tag='before'),marked(9,tag='after'),
        f'tag {select(origin="x=8,y=63.5,z=2,dx=-4,dy=0,dz=0")} add selected'],
       [f'execute if entity {select("tag=low,tag=selected")} if entity {select("tag=high,tag=selected")} if entity {select("tag=before,tag=!selected")} if entity {select("tag=after,tag=!selected")}'])

for ordering,chosen,other in [('nearest','near','far'),('furthest','far','near')]:
    entity('selector-'+ordering+'-limit','Select the '+ordering+' entity before limiting',
           'A deterministic distance ordering selects exactly the intended fixture before applying limit one.',
           [marked(2,tag='near'),marked(6,tag='far'),
            f'tag {select("sort="+ordering+",limit=1",origin="x=0.5,y=63.5,z=2,dx=8,dy=0,dz=0")} add selected'],
           [f'execute if entity {select("tag="+chosen+",tag=selected")} if entity {select("tag="+other+",tag=!selected")}'])

entity('selector-limit-count','Limit caps execution multiplicity',
       'Three fixtures produce exactly two execution branches when limit two is applied.',
       [marked(2,tag='near'),marked(4,tag='middle'),marked(6,tag='far'),
        'scoreboard players set count pp 0',
        f'execute as {select("sort=nearest,limit=2",origin="x=0.5,y=63.5,z=2,dx=8,dy=0,dz=0")} run scoreboard players add count pp 1'],
       ['execute if score count pp matches 2'],setup=['scoreboard objectives add pp dummy'],cleanup=['scoreboard objectives remove pp'])

entity('selector-quoted-name','Quoted custom names filter entities',
       'A name containing a space selects its fixture and excludes a differently named control.',
       [marked(2,tag='named',data='CustomName:{text:"Parity Marker"}'),marked(4,tag='other',data='CustomName:{text:"Other"}'),
        f'tag {select("name=\"Parity Marker\"")} add selected'],
       [f'execute if entity {select("tag=named,tag=selected")} if entity {select("tag=other,tag=!selected")}'])

entity('selector-empty-tag','Empty tag predicates distinguish tagged entities',
       'All fixtures carry pp: tag=! must accept them while tag= must reject them.',
       [marked()],
       [f'execute if entity {select("tag=!")} unless entity {select("tag=")}'])

entity('selector-nbt-empty-list','Empty NBT lists are not wildcards',
       'A populated Tags list satisfies a nonempty subset but must not satisfy the empty-list pattern.',
       [marked()],
       [f'execute if entity {select("nbt={Tags:[\"pp\"]}")} unless entity {select("nbt={Tags:[]}")}'],category='entity-nbt')

entity('selector-nbt-list-cardinality','NBT list patterns cannot exceed actual list length',
       'A two-tag fixture rejects a three-element pattern even with repeated values, while a repeated two-element subset still matches.',
       [marked()],
       [f'execute if entity {select("nbt={Tags:[\"fixture\",\"fixture\"]}")} unless entity {select("nbt={Tags:[\"fixture\",\"fixture\",\"fixture\"]}")}'],category='entity-nbt')

entity('selector-nbt-list-compounds','NBT list matching keeps compound fields together',
       'Unordered compound subsets match extra fields, but fields from different list entries cannot be combined.',
       [marked(data='data:{rows:[{key:"a",value:1,extra:9},{key:"b",value:3}]}')],
       [f'execute if entity {select("nbt={data:{rows:[{key:\"b\"},{key:\"a\",value:1}]}}") } unless entity {select("nbt={data:{rows:[{key:\"b\",value:1}]}}") }'],category='entity-nbt')

entity('selector-nbt-numeric-type','NBT matching preserves numeric tag types',
       'A byte value and an integer with equal magnitude remain distinct NBT selector matches.',
       [marked(2,tag='byte',data='data:{value:1b}'),marked(4,tag='integer',data='data:{value:1}'),
        f'tag {select("nbt={data:{value:1b}}")} add selected'],
       [f'execute if entity {select("tag=byte,tag=selected")} if entity {select("tag=integer,tag=!selected")}'],category='entity-nbt')

entity('selector-nbt-inverted','Inverted NBT predicates exclude matching data',
       'NBT inversion selects the nonmatching fixture and retains the matching fixture without mutation.',
       [marked(2,tag='match',data='data:{value:7}'),marked(4,tag='other',data='data:{value:9}'),
        f'tag {select("nbt=!{data:{value:7}}")} add selected'],
       [f'execute if entity {select("tag=match,tag=!selected")} if entity {select("tag=other,tag=selected")}'],category='entity-nbt')

entity('selector-rotation-axes','Yaw and pitch filters use their respective axes',
       'A marker with yaw ninety and pitch twenty passes independent yaw/pitch ranges and fails swapped ranges.',
       [marked(data='Rotation:[90.0f,20.0f]')],
       [f'execute if entity {select("y_rotation=80..100,x_rotation=10..30")} unless entity {select("x_rotation=80..100")} unless entity {select("y_rotation=10..30")}'])

entity('selector-rotation-wrap','Yaw ranges can cross the signed angle boundary',
       'A wraparound yaw range includes negative 175 degrees and excludes zero.',
       [marked(2,tag='inside',data='Rotation:[-175.0f,0.0f]'),marked(4,tag='outside',data='Rotation:[0.0f,0.0f]'),
        f'tag {select("y_rotation=170..-170")} add selected'],
       [f'execute if entity {select("tag=inside,tag=selected")} if entity {select("tag=outside,tag=!selected")}'])

entity('entity-nbt-remove','Remove deletes only the selected NBT child',
       'Removing one nested marker field preserves its sibling and the parent compound.',
       [marked(data='data:{nested:{remove:3,keep:9}}'),
        positive(f'execute if entity {select("nbt={data:{nested:{remove:3,keep:9}}}")}'),
        f'data remove entity {select("limit=1")} data.nested.remove'],
       [f'execute if entity {select("nbt={data:{nested:{keep:9}}}")} unless data entity {select("limit=1")} data.nested.remove'],category='entity-nbt')

for operation,mutation,expected in [('set-index','data.values[1] set value 6',6),('remove-index','data.values[1]',8)]:
    verb='modify' if operation=='set-index' else 'remove'
    entity('entity-nbt-'+operation,'NBT list '+operation.replace('-',' '),
           'An indexed list mutation is observed by reading the resulting numeric element, preserving index semantics.',
           [marked(data='data:{values:[2,4,8]}'),
            f'execute store result score value pp run data get entity {select("limit=1")} data.values[1]',
            positive('execute if score value pp matches 4'),
            f'data {verb} entity {select("limit=1")} {mutation}',
            f'execute store result score value pp run data get entity {select("limit=1")} data.values[1]'],
           [f'execute if score value pp matches {expected}'],setup=['scoreboard objectives add pp dummy'],cleanup=['scoreboard objectives remove pp'],category='entity-nbt')

entity('entity-teleport-relative','Relative teleport uses the executing entity position',
       'Execution at a marker offsets its own position by one on each axis without integer recentering.',
       [marked(),f'execute as {select("limit=1")} at @s run teleport @s ~1 ~1 ~-1'],
       [f'execute if entity {select(origin="x=3.5,y=65,z=1.5,distance=..0.01")} unless entity {select(origin="x=2.5,y=64,z=2.5,distance=..0.01")}'])

entity('entity-teleport-fractional','Decimal teleport coordinates remain exact',
       'A decimal destination with negative x retains fractions rather than centering on block coordinates.',
       [marked(),f'teleport {select("limit=1")} -1.25 65.5 6.75'],
       [f'execute if entity {select(origin="x=-1.25,y=65.5,z=6.75,distance=..0.01")} unless entity {select(origin="x=-0.75,y=65.5,z=7.25,distance=..0.01")}'])

entity('entity-cleanup-distance','Spatial kill preserves entities outside its radius',
       'After both fixtures are proven present, a bounded distance kill removes the near fixture and preserves the far fixture.',
       [marked(2,tag='near'),marked(8,tag='far'),
        positive(f'execute if entity {select("tag=near")} if entity {select("tag=far")}'),
        f'kill {select(origin="x=0.5,y=64,z=2.5,distance=..3")}'],
       [f'execute if entity {select("tag=far")} unless entity {select("tag=near")}'])

STAND=select('limit=1',kind='minecraft:armor_stand')
STANDS=select(kind='minecraft:armor_stand')
STAND_SUMMON='summon minecraft:armor_stand 2 64 2 {Tags:["pp"],NoGravity:1b,Invulnerable:1b}'

def effect_case(id,title,description,commands,probes):
    case(id,title,'entity-effects',description,[STAND_SUMMON,*commands],probes,
         setup=[f'execute if entity {STANDS} run kill {STANDS}'],
         cleanup=[f'execute if entity {STANDS} run kill {STANDS}'],
         notes='Observes active_effects NBT on a summoned armor stand with frozen simulation, without a connected player. No inventory, combat or elapsed-tick claim.')

effect_case('entity-effect-fields','Effect application stores entity-observable fields',
            'A speed effect stores duration in ticks, zero-based amplifier, and hidden particles/icon on an armor stand.',
            [f'effect give {STAND} minecraft:speed 60 2 true'],
            [f'execute if entity {select("nbt={active_effects:[{id:\"minecraft:speed\",duration:1200,amplifier:2b,show_particles:0b,show_icon:0b}]}",kind="minecraft:armor_stand")}'])

effect_case('entity-effect-clear-selective','Clearing one effect preserves another',
            'After both speed and glowing are observed, clearing speed leaves glowing on the same armor stand.',
            [f'effect give {STAND} minecraft:speed 60 0 true',f'effect give {STAND} minecraft:glowing 60 0 true',
             positive(f'execute if entity {select("nbt={active_effects:[{id:\"minecraft:speed\"},{id:\"minecraft:glowing\"}]}",kind="minecraft:armor_stand")}'),
             f'effect clear {STAND} minecraft:speed'],
            [f'execute if entity {select("nbt={active_effects:[{id:\"minecraft:glowing\"}]}",kind="minecraft:armor_stand")} unless entity {select("nbt={active_effects:[{id:\"minecraft:speed\"}]}",kind="minecraft:armor_stand")}'])

if __name__=='__main__':
    directory=ROOT/'scenarios';directory.mkdir(exist_ok=True)
    for scenario in CASES:
        (directory/(scenario['id']+'.json')).write_text(json.dumps(scenario,indent=2)+'\n')
    print(f'Authored {len(CASES)} distinct scenarios')
