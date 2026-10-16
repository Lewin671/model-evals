import {appendFileSync, writeFileSync} from 'node:fs';
import {execFile} from 'node:child_process';
const change = JSON.parse(process.env.MODEL_EVAL_CHANGE || '""');

export default function (cmd) {
  let round = 0;
  let changed = false;
  let outputTokens = 0;
  const names = ['repo_read', 'repo_write', 'repo_test'];
  const record = data => {
    if (process.env.MODEL_EVAL_CONTROL) {
      writeFileSync(process.env.MODEL_EVAL_CONTROL, JSON.stringify({round, change_delivered: changed, outputTokens, active_tools:cmd.getActiveTools(), ...data}));
    }
  };
  const dispatch = action => new Promise((resolve) => {
    const payload = {root:process.env.MODEL_EVAL_WORKSPACE, seed:process.env.MODEL_EVAL_SEED,
      variant:process.env.MODEL_EVAL_VARIANT, change:changed, action};
    const child=execFile(process.env.MODEL_EVAL_PYTHON,[process.env.MODEL_EVAL_BRIDGE],
      {timeout:60000,maxBuffer:4*1024*1024},(error,stdout) => {
        let result;
        try {result=JSON.parse(stdout);} catch {result={error:'Evaluation bridge failed'};}
        if(process.env.MODEL_EVAL_TOOL_LOG) appendFileSync(process.env.MODEL_EVAL_TOOL_LOG,JSON.stringify({round,action,result})+'\n');
        resolve(result.error ? {ok:false,error:result.error} : {ok:true,content:[{type:'text',text:JSON.stringify(result)}]});
      });
    child.stdin.end(JSON.stringify(payload));
  });
  let serial = Promise.resolve();
  const bridge = action => {
    const result=serial.then(()=>dispatch(action));
    serial=result.then(()=>undefined,()=>undefined);
    return result;
  };
  cmd.addTool({schema:{name:'repo_read',description:'Read repository files. This is the repository read tool for this evaluation.',
    input_schema:{type:'object',properties:{paths:{type:'array',items:{type:'string',enum:['README.md','ledger/__init__.py','ledger/parser.py','ledger/store.py','ledger/api.py']}}},required:['paths'],additionalProperties:false}},
    readOnly:true,shouldDefer:false,run:({input})=>bridge({tool:'read',paths:input.paths})});
  cmd.addTool({schema:{name:'repo_write',description:'Replace complete contents of one or more of the three editable source files.',
    input_schema:{type:'object',properties:{files:{type:'object',properties:{'ledger/api.py':{type:'string'},'ledger/parser.py':{type:'string'},'ledger/store.py':{type:'string'}},additionalProperties:false}},required:['files'],additionalProperties:false}},
    readOnly:false,shouldDefer:false,run:({input})=>bridge({tool:'write',files:input.files})});
  cmd.addTool({schema:{name:'repo_test',description:'Run public repository checks; returns inputs, expected values and observed behavior. Use instead of shell or other test tools.',
    input_schema:{type:'object',properties:{},additionalProperties:false}},readOnly:true,shouldDefer:false,run:()=>bridge({tool:'test'})});
  cmd.setActiveTools(names);
  cmd.hooks({
    onTurnStart:({state,turnNumber})=>{
      round=turnNumber;
      if(round>=3) changed=true;
      cmd.setActiveTools(names);record({active_tools:cmd.getActiveTools()});return state;
    },
    appendSystemPrompt:()=> 'This coding evaluation provides exactly three repository tools: repo_read, repo_write and repo_test. Use these native tools. Do not use shell, web, subagents, or the ordinary filesystem tools. '+(changed ? '\nConsumer change request (part of final acceptance):\n'+change : ''),
    onStop:()=>{
      if(!changed){changed=true;record({});return {continue:true,reason:change};}
      return {continue:false};
    },
    shouldStopAfterTurn:()=>outputTokens>=Number(process.env.MODEL_EVAL_OUTPUT_BUDGET || 32000),
  });
  cmd.on('model_request_end',event=>{outputTokens+=event.usage?.outputTokens || 0;record({});});
}
