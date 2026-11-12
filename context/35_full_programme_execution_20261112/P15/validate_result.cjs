/* Structural display gate; not market, financial or operational acceptance. */
const fs=require('node:fs'),vm=require('node:vm');
const ctx={module:{exports:{}}};vm.runInNewContext(fs.readFileSync(__dirname+'/source/adapter.js','utf8'),ctx);
const p=JSON.parse(fs.readFileSync(0,'utf8'));ctx.module.exports.validate(p);
process.stdout.write(JSON.stringify({status:'PASS_STRUCTURE_ONLY',evaluations:p.evaluations.length})+'\n');
