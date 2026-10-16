"""Frozen authored counterfactual pairs with deterministic outcome checks."""
import json
from ..grading import execute

RULES='Answer directly with one JSON object, no Markdown fences or explanation. Do not call CLI tools, inspect local files, or delegate. All task information is supplied below. This is a bounded text-based evaluation. '
STARTER='''def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        key = b['delivery']
        if key in seen:
            continue
        seen.add(key)
        try:
            for amount in b['amounts']:
                balances[b['account']] = balances.get(b['account'], 0) + int(amount)
            accepted += 1
        except ValueError:
            pass
    return {'balances': balances, 'accepted': accepted}
'''

def reference(scoped):
    key="(b['account'], b['delivery'])" if scoped else "b['delivery']"
    return f'''def solve(batches):
    balances, seen = {{}}, set()
    accepted = 0
    for b in batches:
        key = {key}
        if key in seen:
            continue
        try:
            delta = sum(int(x) for x in b['amounts'])
        except ValueError:
            continue
        balances[b['account']] = balances.get(b['account'], 0) + delta
        seen.add(key)
        accepted += 1
    return {{'balances': balances, 'accepted': accepted}}
'''

CASES=[[],[{'account':'a','delivery':'d','amounts':['3','bad']},{'account':'a','delivery':'d','amounts':['7']}],
    [{'account':'a','delivery':'d','amounts':['4']},{'account':'b','delivery':'d','amounts':['9']}],
    [{'account':'a','delivery':'d','amounts':['4']},{'account':'a','delivery':'d','amounts':['99']}],
    [{'account':'a','delivery':'x','amounts':[]},{'account':'a','delivery':'y','amounts':['-4','+7']}],
    [{'account':'a','delivery':'d','amounts':['bad']},{'account':'b','delivery':'d','amounts':['8']},{'account':'a','delivery':'d','amounts':['2']}]]

def code_expected(scoped):
    # Independent fold: validate the entire batch before selecting distinct keys.
    out=[]
    for batches in CASES:
        selected={}
        for b in batches:
            try: amounts=list(map(int,b['amounts']))
            except ValueError:continue
            key=(b['account'],b['delivery']) if scoped else b['delivery']
            selected.setdefault(key,(b['account'],sum(amounts)))
        accounts={a for a,_ in selected.values()}
        out.append({'balances':{a:sum(v for account,v in selected.values() if account==a) for a in accounts},'accepted':len(selected)})
    return out


def task(domain,variant):
    changed=variant=='B'
    if domain=='coding':
        scope='per account' if changed else 'globally across all accounts'
        prompt=RULES+f'''Repair solve below. Delivery IDs are unique {scope}. A valid delivery is applied once; ignore its later retries even if contents differ. A batch containing any invalid integer must have no effects, must not consume its delivery ID, and must not create an account. A corrected retry may succeed. Empty valid batches count and create zero balance. Do not mutate input. Inputs have the shown shape; amounts are integer strings or invalid strings. Return {{"source":"complete Python solve function"}}, at most 35 lines.\n{STARTER}'''
        return {'id':domain+'-'+variant,'domain':domain,'variant':variant,'prompt':prompt,'scoped':changed,'calls':1}
    if domain=='everyday':
        status='DRAFT, not approved' if changed else 'APPROVED'
        prompt=RULES+f'''It is 08:45 on Oct 20. Choose the lowest incremental cash-cost plan to attend an in-person meeting on Oct 22. Original confirmed meeting: 11:00. Later email: "Move to 10:30", status {status}. Only approved changes override confirmed arrangements. You must reach the venue 20 minutes before the applicable meeting time. No other constraints. Existing unused ticket cost 280, already paid. Cancelling by 09:00 today yields a 100 cash refund; afterwards zero. All new tickets are available and must be bought now. Airport-to-venue transfer costs/time and bags below are mandatory. Only a prior-evening arrival needs one 90 hotel night. F1: Oct22 arrival09:20, fare240, bag35, transfer45min/cost18. F2: Oct22 arrival10:00, fare180, bag0, transfer30min/cost30. F3: Oct21 arrival21:00, fare130, bag25, transfer30min/cost18. Define incremental cost as new fare+bag+transfer+hotel minus refund; exclude sunk 280. Return {{"flight":"F?","meeting":"HH:MM","cancel_now":true,"incremental_cost":integer}}.'''
        expected={'flight':'F2' if changed else 'F3','meeting':'11:00' if changed else '10:30','cancel_now':True,'incremental_cost':110 if changed else 163}
        return {'id':domain+'-'+variant,'domain':domain,'variant':variant,'prompt':prompt,'expected':expected,'calls':1}
    if domain=='browser':
        initial=RULES+'''You operate a deterministic shopping simulator, not a real browser. Buy the cheapest eligible annual plan for a 6-person team, including a shared audit export. No purchase/payment is executed; save a comparison artifact. All prices USD. Initial search results: A "Team 84/year"; B "Team 96/year"; C "Pro 70/year". Page IDs A,B,C are available through inspect. First return {"action":"inspect","pages":[...]} for the detail pages you need. You get one observation then must save your choice. Search titles alone are not binding offers.'''
        details={'A':{'annual_base':84,'included_seats':3,'extra_seat_annual':8,'audit_export':'included'},'B':{'annual_base':96,'included_seats':6,'extra_seat_annual':0,'audit_export':'included'},'C':{'annual_base':70,'max_seats':5,'audit_export':'included'}}
        # Live renewal quote differs from the search and detail prices.
        live={'A':{'all_in_annual':92 if changed else 108,'seats':6,'audit_export':'included'},'B':{'all_in_annual':104,'seats':6,'audit_export':'included'},'C':{'all_in_annual':70,'seats':5,'audit_export':'included'}}
        expected={'action':'save','plan':'A' if changed else 'B','annual_total':92 if changed else 104}
        return {'id':domain+'-'+variant,'domain':domain,'variant':variant,'prompt':initial,'details':details,'live':live,'expected':expected,'calls':2}
    if domain=='desktop':
        status='approved' if changed else 'draft'
        initial=RULES+f'''You operate a deterministic workbook simulator, not a real computer. Export approved reimbursements from the highest numbered APPROVED workbook revision into reimbursements.csv. Use underlying rows including filtered-out rows; exclude voided rows. Group by employee; convert USD to cents using exact decimal arithmetic. Employee keys trim whitespace and compare case-insensitively; output lowercase. Source workbooks must stay unchanged. Manifest: r1.xlsx revision1 approved; r2.xlsx revision2 approved; r3.xlsx revision3 {status} (most recently edited). First return {{"action":"open","files":[...]}}. You receive the requested workbook states, then must export. Final export schema will be supplied with the observation.'''
        files={
            'r1.xlsx':{'visible_filter':'approved','rows':[['Ada','approved','1.00',True]]},
            'r2.xlsx':{'visible_filter':'employee=ada','rows':[[' Ada ','approved','10.10',True],['ada','approved','0.20',True],['BO','approved','7.05',False],['bo','voided','50.00',False],['cy','pending','3.00',False]]},
            'r3.xlsx':{'visible_filter':'employee=ada','rows':[[' Ada ','approved','10.10',True],['ada','voided','0.20',True],['BO','approved','7.05',False],['bo','approved','-2.00',False],['cy','pending','3.00',False]]}}
        expected={'action':'export','source':'r3.xlsx' if changed else 'r2.xlsx','destination':'reimbursements.csv','rows':[['ada',1010],['bo',505]] if changed else [['ada',1030],['bo',705]]}
        return {'id':domain+'-'+variant,'domain':domain,'variant':variant,'prompt':initial,'files':files,'expected':expected,'calls':2}
    raise ValueError(domain)


def suite():
    # Separate paired cases in the schedule. No paired answers enter model context.
    return [task(d,v) for v in ('A','B') for d in ('coding','everyday','browser','desktop')]


def decode(text):
    text=text.strip()
    if text.startswith('```') and text.endswith('```'):text='\n'.join(text.splitlines()[1:-1])
    value=json.loads(text)
    if not isinstance(value,dict):raise ValueError('expected object')
    return value


def observe(t,action):
    if t['domain']=='browser':
        ids=action.get('pages',[]) if action.get('action')=='inspect' else []
        if not isinstance(ids,list) or any(not isinstance(i,str) or i not in t['details'] for i in ids):ids=[]
        return {'detail_pages':{i:t['details'][i] for i in ids},'checkout_update':{i:t['live'][i] for i in ids},
            'notice':'Final checkout quotes supersede earlier prices and include all required seats/features/taxes. Save the cheapest eligible plan. Return {"action":"save","plan":"ID","annual_total":integer}.'}
    ids=action.get('files',[]) if action.get('action')=='open' else []
    if not isinstance(ids,list) or any(not isinstance(i,str) or i not in t['files'] for i in ids):ids=[]
    return {'workbooks':{i:t['files'][i] for i in ids},'row_columns':['employee','status','amount_usd','visible'],
        'notice':'Return {"action":"export","source":"filename","destination":"reimbursements.csv","rows":[["employee",integer_cents],...]}. Rows sorted by employee. This action creates a separate CSV artifact; source workbooks are read-only.'}


def grade(t,answer):
    if t['domain']=='coding':
        source=answer.get('source')
        if not isinstance(source,str):return {'passed':0,'total':len(CASES),'reason':'missing source','complete':False}
        try: actual=execute(source,CASES)
        except (ValueError,TimeoutError):return {'passed':0,'total':len(CASES),'reason':'candidate execution failed','complete':False}
        checks=[a.get('value')==e and not a.get('mutated',True) for a,e in zip(actual,code_expected(t['scoped']))]
        return {'passed':sum(checks),'total':len(CASES),'complete':len(checks)==len(CASES) and all(checks),'checks':checks}
    expected=t['expected']
    checks={k:answer.get(k)==v for k,v in expected.items()}
    return {'passed':sum(checks.values()),'total':len(checks),'complete':all(checks.values()),'checks':checks}


def qualify():
    for scoped in (False,True):
        t=task('coding','B' if scoped else 'A')
        assert grade(t,{'source':reference(scoped)})['complete']
        assert not grade(t,{'source':STARTER})['complete']
        assert not grade(t,{'source':reference(not scoped)})['complete']
    # Independent enumeration validates the travel arithmetic and feasibility.
    for variant,meeting in [('A',630),('B',660)]:
        plans=[('F1',560+45,240+35+18),('F2',600+30,180+30),('F3',-180,130+25+18+90)]
        feasible=[(cost-100,name) for name,arrival,cost in plans if arrival+20<=meeting]
        expected=task('everyday',variant)['expected']
        assert min(feasible)==(expected['incremental_cost'],expected['flight'])
    for domain in ('everyday','browser','desktop'):
        for variant in ('A','B'):
            t=task(domain,variant)
            assert grade(t,t['expected'])['complete']
            assert not grade(t,task(domain,'B' if variant=='A' else 'A')['expected'])['complete']
    return {'reference':'pass','starter':'fails','counterfactual_transplants':'fail','travel_enumeration':'pass'}
