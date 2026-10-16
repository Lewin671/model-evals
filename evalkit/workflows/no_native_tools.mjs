import {writeFileSync} from 'node:fs';

export default function (cmd) {
  cmd.setActiveTools([]);
  cmd.hooks({
    onTurnStart: ({state}) => {
      cmd.setActiveTools([]);
      const active = cmd.getActiveTools();
      const proof = process.env.MODEL_EVAL_TOOL_PROOF;
      if (proof) writeFileSync(proof, JSON.stringify({active_tools: active}));
      return state;
    },
    appendSystemPrompt: () => 'This evaluation has no native tools. Return JSON file-tool actions in the final response, as requested by the user. The host executes those actions and returns observations in the next request. Do not call native read_file, shell, or other function tools.',
  });
}
