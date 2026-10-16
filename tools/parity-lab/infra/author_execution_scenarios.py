"""Distinct command-state cases for execute and scoreboard semantics."""
from copy import deepcopy
import json
from pathlib import Path

SEL='@e[type=minecraft:marker,tag=pp,x=-32,y=48,z=-32,dx=64,dy=48,dz=64]'
CASES=[]


def probe(conditions):
    return {'command':'execute '+conditions,'observe':True,'expect_contains':'Test passed'}


def case(id,title,description,commands,conditions,*,entities=False,second=False,category='scoreboard'):
    cleanup_entities=f'execute if entity {SEL} run kill {SEL}'
    setup=['tick freeze','scoreboard objectives add pp_exec dummy']
    cleanup=['scoreboard objectives remove pp_exec','tick unfreeze']
    if second:
        setup.append('scoreboard objectives add pp_aux dummy')
        cleanup.insert(0,'scoreboard objectives remove pp_aux')
    if entities:
        setup.insert(1,cleanup_entities)
        cleanup.insert(0,cleanup_entities)
    CASES.append({'schema_version':1,'id':id,'title':title,'category':category,
                  'description':description,'tags':['command','deterministic','state-observation','execution-campaign'],
                  'setup':setup,'steps':[{'command':c} if isinstance(c,str) else c for c in commands]+[probe(conditions)],
                  'cleanup':cleanup,
                  'notes':'Vanilla 26.3 reference expectations are checked live; raw responses remain in campaign artifacts. '
                          'Simulation is frozen and restored in cleanup. Positive state probes fail on empty or rejected output. '
                          'Current-source console validation is separate from RCON support. No client or elapsed-tick claim.'})


def setscore(holder,value,objective='pp_exec'):
    return f'scoreboard players set {holder} {objective} {value}'


def selected(options=''):
    return SEL[:-1]+(','+options if options else '')+']'


def marker(x,tag):
    return f'summon minecraft:marker {x} 64 2 {{Tags:["pp","{tag}"]}}'


case('score-wrap-add-remove','Addition and removal wrap signed boundaries',
     'Adding at MAX wraps to MIN, then removing one wraps back to MAX.',
     [setscore('value',2147483647),'scoreboard players add value pp_exec 1',
      probe('if score value pp_exec matches -2147483648'),'scoreboard players remove value pp_exec 1'],
     'if score value pp_exec matches 2147483647')
case('score-wrap-multiply','Multiplication wraps rather than clamps',
     'Multiplying 65536 by itself wraps to zero and preserves the multiplier.',
     [setscore('a',65536),setscore('b',65536),'scoreboard players operation a pp_exec *= b pp_exec'],
     'if score a pp_exec matches 0 if score b pp_exec matches 65536')
case('score-division-overflow','MIN divided by minus one wraps',
     'The signed division overflow case returns MIN without disconnecting or changing its divisor.',
     [setscore('a',-2147483648),setscore('b',-1),'scoreboard players operation a pp_exec /= b pp_exec'],
     'if score a pp_exec matches -2147483648 if score b pp_exec matches -1')
case('score-negative-divisor-floor','Positive dividend uses floor with negative divisor',
     'Seven divided by minus three rounds down to minus three, preserving the divisor.',
     [setscore('a',7),setscore('b',-3),'scoreboard players operation a pp_exec /= b pp_exec'],
     'if score a pp_exec matches -3 if score b pp_exec matches -3')
case('score-negative-divisor-modulo','Remainder follows negative divisor sign',
     'Seven modulo minus three is minus two, rather than the truncating remainder one.',
     [setscore('a',7),setscore('b',-3),'scoreboard players operation a pp_exec %= b pp_exec'],
     'if score a pp_exec matches -2 if score b pp_exec matches -3')
case('score-operation-creates-source','Assignment creates absent source and target scores',
     'After proving both holders absent, assignment materializes both scores as zero.',
     [setscore('control',1),probe('if score control pp_exec matches 1 unless score source pp_exec matches -2147483648..2147483647 unless score target pp_exec matches -2147483648..2147483647'),
      'scoreboard players operation target pp_exec = source pp_exec'],
     'if score source pp_exec matches 0 if score target pp_exec matches 0')
case('score-reset-one-objective','Reset removes one objective score and preserves another',
     'An observed pair of scores becomes one absent score and one preserved score after an objective-specific reset.',
     [setscore('value',7),setscore('value',9,'pp_aux'),probe('if score value pp_exec matches 7 if score value pp_aux matches 9'),
      'scoreboard players reset value pp_exec'],
     'if score value pp_aux matches 9 unless score value pp_exec matches -2147483648..2147483647',second=True)
case('score-objective-recreation','Removing an objective clears its stored scores',
     'Removing and recreating the same objective loses the old holder score while a new control can be set.',
     [setscore('old',7),probe('if score old pp_exec matches 7'),'scoreboard objectives remove pp_exec',
      'scoreboard objectives add pp_exec dummy',setscore('control',1)],
     'if score control pp_exec matches 1 unless score old pp_exec matches -2147483648..2147483647')
case('score-compare-strict','Strict comparisons reject equality at signed extremes',
     'Less-than and greater-than order MIN and MAX correctly and both reject equal operands.',
     [setscore('lo',-2147483648),setscore('hi',2147483647)],
     'if score lo pp_exec < hi pp_exec if score hi pp_exec > lo pp_exec unless score lo pp_exec < lo pp_exec unless score hi pp_exec > hi pp_exec')
case('score-compare-inclusive','Inclusive comparisons accept equality and ordered values',
     'Both inclusive operators accept equal operands but reject reversed inequalities.',
     [setscore('a',-1),setscore('b',0)],
     'if score a pp_exec <= a pp_exec if score b pp_exec >= b pp_exec if score a pp_exec <= b pp_exec if score b pp_exec >= a pp_exec unless score a pp_exec >= b pp_exec unless score b pp_exec <= a pp_exec')
case('score-compare-cross-objective','Equality compares values across objectives',
     'Equal cross-objective values match before a mutation and differ afterward.',
     [setscore('a',7),setscore('a',7,'pp_aux'),probe('if score a pp_exec = a pp_aux'),
      'scoreboard players add a pp_aux 1'],
     'if score a pp_exec matches 7 if score a pp_aux matches 8 unless score a pp_exec = a pp_aux',second=True)
case('score-match-range-endpoints','Score ranges include endpoints and open extremes',
     'Closed endpoints, open lower and upper bounds, and full signed extremes accept only the intended scores.',
     [setscore('lo',-2147483648),setscore('mid',-2),setscore('hi',2147483647)],
     'if score lo pp_exec matches ..-2 if score mid pp_exec matches -2..-2 if score hi pp_exec matches -2.. unless score mid pp_exec matches ..-3 unless score mid pp_exec matches -1..')
case('execute-missing-score-condition','Missing score conditions do not create a zero score',
     'If rejects a missing score while unless accepts it; neither condition materializes the missing holder.',
     [setscore('count',0),'execute if score absent pp_exec matches 0 run scoreboard players add count pp_exec 10',
      'execute unless score absent pp_exec matches 0 run scoreboard players add count pp_exec 1'],
     'if score count pp_exec matches 1 unless score absent pp_exec matches -2147483648..2147483647',category='execute')
case('execute-condition-chain','Every condition gates the final mutation',
     'A false early condition and a false late condition each block mutation; the all-true control runs once.',
     [setscore('gate',1),setscore('count',0),
      'execute if score gate pp_exec matches 0 if score gate pp_exec matches 1 run scoreboard players add count pp_exec 10',
      'execute if score gate pp_exec matches 1 if score gate pp_exec matches 0 run scoreboard players add count pp_exec 100',
      'execute if score gate pp_exec matches 1 if score gate pp_exec matches 1 run scoreboard players add count pp_exec 1'],
     'if score count pp_exec matches 1 if score gate pp_exec matches 1',category='execute')
case('execute-unless-chain','Unless predicates gate mutations after state changes',
     'An unless branch changes the gate, which prevents the same branch from running twice; its inverse then runs.',
     [setscore('gate',0),setscore('count',0),
      'execute unless score gate pp_exec matches 1 run scoreboard players set gate pp_exec 1',
      'execute unless score gate pp_exec matches 1 run scoreboard players add count pp_exec 10',
      'execute if score gate pp_exec matches 1 unless score count pp_exec matches 1 run scoreboard players add count pp_exec 1'],
     'if score gate pp_exec matches 1 if score count pp_exec matches 1',category='execute')
case('execute-as-self-scores','Execute as keeps a separate score for each self',
     'Two marker executors each receive and increment their own score while a tagged third marker stays unchanged.',
     [marker(2,'first'),marker(4,'second'),marker(6,'other'),f'scoreboard players set {SEL} pp_exec 3',
      f'execute as {selected("tag=!other")} run scoreboard players add @s pp_exec 2'],
     f'if entity {selected("tag=first,scores={pp_exec=5}")} if entity {selected("tag=second,scores={pp_exec=5}")} if entity {selected("tag=other,scores={pp_exec=3}")}',entities=True,category='execute')
case('selector-score-range','Score selector includes both interval endpoints',
     'Scores at two and four are selected by 2..4; an exterior score is preserved as an excluded control.',
     [marker(2,'lower'),marker(4,'upper'),marker(6,'outside'),
      f'scoreboard players set {selected("tag=lower")} pp_exec 2',f'scoreboard players set {selected("tag=upper")} pp_exec 4',
      f'scoreboard players set {selected("tag=outside")} pp_exec 5',f'tag {selected("scores={pp_exec=2..4}")} add selected'],
     f'if entity {selected("tag=lower,tag=selected")} if entity {selected("tag=upper,tag=selected")} if entity {selected("tag=outside,tag=!selected")}',entities=True)
case('selector-score-intersection','Multiple score filters intersect',
     'Only the marker satisfying both objective ranges receives the selected tag; each single-range control survives unselected.',
     [marker(2,'both'),marker(4,'first'),marker(6,'second'),f'scoreboard players set {SEL} pp_exec 0',f'scoreboard players set {SEL} pp_aux 0',
      f'scoreboard players set {selected("tag=both")} pp_exec 1',f'scoreboard players set {selected("tag=both")} pp_aux 2',
      f'scoreboard players set {selected("tag=first")} pp_exec 1',f'scoreboard players set {selected("tag=second")} pp_aux 2',
      f'tag {selected("scores={pp_exec=1,pp_aux=2}")} add selected'],
     f'if entity {selected("tag=both,tag=selected")} if entity {selected("tag=first,tag=!selected")} if entity {selected("tag=second,tag=!selected")}',entities=True,second=True)
case('selector-score-absent','Score selectors distinguish absent from zero',
     'Two observed fixtures are excluded with missing scores, selected with explicit zero scores, and excluded again after reset.',
     [marker(2,'fixture'),marker(4,'fixture'),setscore('count',0),
      f'execute as {SEL} run scoreboard players add count pp_exec 1',probe('if score count pp_exec matches 2'),
      setscore('count',0),f'execute as {selected("scores={pp_exec=0}")} run scoreboard players add count pp_exec 1',
      probe('if score count pp_exec matches 0'),f'scoreboard players set {SEL} pp_exec 0',
      setscore('count',0),f'execute as {selected("scores={pp_exec=0}")} run scoreboard players add count pp_exec 1',
      probe('if score count pp_exec matches 2'),f'scoreboard players reset {SEL} pp_exec',
      setscore('count',0),f'execute as {selected("scores={pp_exec=0}")} run scoreboard players add count pp_exec 1'],
     'if score count pp_exec matches 0',entities=True)
case('selector-score-holder-identity','Score selectors use each entity score holder',
     'Two markers with UUID-backed scores match seven while a fake holder named marker with value 99 does not affect either entity.',
     [marker(2,'fixture'),marker(4,'fixture'),setscore('count',0),
      f'execute as {SEL} run scoreboard players add count pp_exec 1',probe('if score count pp_exec matches 2'),
      f'scoreboard players set {SEL} pp_exec 7',setscore('marker',99),setscore('count',0),
      f'execute as {selected("scores={pp_exec=7}")} run scoreboard players add count pp_exec 1',
      probe('if score count pp_exec matches 2'),setscore('count',0),
      f'execute as {selected("scores={pp_exec=99}")} run scoreboard players add count pp_exec 1'],
     'if score count pp_exec matches 0 if score marker pp_exec matches 99',entities=True)
case('execute-store-signed-result','Store result preserves a signed command result',
     'Storing scoreboard get captures a negative value exactly and leaves its source intact.',
     [setscore('source',-7),setscore('stored',99),'execute store result score stored pp_exec run scoreboard players get source pp_exec'],
     'if score source pp_exec matches -7 if score stored pp_exec matches -7',category='execute')
case('execute-store-success','Store success records both successful and failed conditions',
     'A true terminal condition stores one and a false terminal condition overwrites a sentinel with zero.',
     [setscore('gate',1),setscore('yes',99),setscore('no',99),
      'execute store success score yes pp_exec if score gate pp_exec matches 1',
      'execute store success score no pp_exec if score gate pp_exec matches 0'],
     'if score yes pp_exec matches 1 if score no pp_exec matches 0 if score gate pp_exec matches 1',category='execute')
case('execute-store-operation-total','Store result sums final target scores once',
     'A multi-source operation adds two marker scores to one target and stores its final value once.',
     [marker(2,'first'),marker(4,'second'),f'scoreboard players set {SEL} pp_exec 2',setscore('target',1),
      f'execute store result score result pp_exec run scoreboard players operation target pp_exec += {SEL} pp_exec'],
     f'if score target pp_exec matches 5 if score result pp_exec matches 5 if entity {selected("tag=first,scores={pp_exec=2}")} if entity {selected("tag=second,scores={pp_exec=2}")}',entities=True,category='execute')


def execution_cases():
    return deepcopy(CASES)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]/'scenarios'
    for scenario in CASES:
        (root/(scenario['id']+'.json')).write_text(json.dumps(scenario,indent=2)+'\n')
    print(f'Authored {len(CASES)} execute/scoreboard cases')
