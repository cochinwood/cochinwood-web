/* Conservative, flat-stack planning example. Equipment and loading plan must be confirmed. */
(function () {
  'use strict';
  // Hapag-Lloyd fleet examples; source links and limitations are on the page.
  var containers = {
    '20': {length:5900,width:2352,height:2395,doorWidth:2340,doorHeight:2292,payload:28130},
    '40': {length:12032,width:2352,height:2395,doorWidth:2340,doorHeight:2292,payload:28750}
  };
  var thicknesses = [6,9,12,16,18,25];
  var sheet = {length:2440,width:1220};
  function calculate(input) {
    var box = containers[input.container];
    if (!box || !thicknesses.includes(input.thickness) ||
        !Number.isFinite(input.density) || input.density < 400 || input.density > 1000 ||
        !Number.isFinite(input.payload) || input.payload <= 0 || input.payload * 1000 > box.payload ||
        !Number.isFinite(input.packing) || input.packing < 0 || input.packing > 5000 ||
        !Number.isFinite(input.clearance) || input.clearance < 0 || input.clearance > 500) {
      return {error:'Check the highlighted inputs. Use a positive payload within the equipment example, density from 400 to 1,000 kg/m³, packing from 0 to 5,000 kg and height allowance from 0 to 500 mm.'};
    }
    if (input.packing >= input.payload * 1000) return {error:'Packing mass must be less than the confirmed cargo payload.'};
    // Flat, lengthwise stacks only: 100 mm total end/side clearance, 50 mm between stacks.
    // Door height caps complete stack height; the allowance includes runners and handling room.
    var along = Math.floor((box.length - 100 + 50) / (sheet.length + 50));
    var across = Math.floor((Math.min(box.width, box.doorWidth) - 100 + 50) / (sheet.width + 50));
    var stackHeight = Math.min(box.height, box.doorHeight) - input.clearance;
    var layers = Math.floor(stackHeight / input.thickness);
    var positions = along * across;
    var volume = sheet.length / 1000 * (sheet.width / 1000) * (input.thickness / 1000);
    var mass = volume * input.density;
    var weightCount = Math.floor((input.payload * 1000 - input.packing) / mass);
    var layoutCount = positions * layers;
    var count = Math.min(weightCount, layoutCount);
    return {count:count,volume:count*volume,panelMass:count*mass,cargoMass:count*mass+input.packing,
      sheetMass:mass,weightCount:weightCount,layoutCount:layoutCount,positions:positions,
      layers:layers,along:along,across:across,stackHeight:stackHeight,
      limit:weightCount < layoutCount ? 'Cargo payload' : 'Flat-stack layout'};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {calculate:calculate,containers:containers};
  if (typeof document === 'undefined') return;
  var root = document.getElementById('cwi-container-calculator');
  if (!root) return;
  var fields = {container:'cwi-calc-box',thickness:'cwi-calc-th',density:'cwi-calc-density',
    payload:'cwi-calc-payload',packing:'cwi-calc-packing',clearance:'cwi-calc-clearance'};
  var controls = {};
  Object.keys(fields).forEach(function (key) { controls[key] = document.getElementById(fields[key]); });
  var results = document.getElementById('cwi-calc-results');
  var error = document.getElementById('cwi-calc-error');
  function output(id, text) { document.getElementById(id).textContent = text; }
  function update() {
    var values = {};
    Object.keys(controls).forEach(function (key) {
      values[key] = key === 'container' ? controls[key].value : controls[key].valueAsNumber || Number(controls[key].value);
      if (key !== 'container' && controls[key].value.trim() === '') values[key] = NaN;
    });
    controls.payload.max = String(containers[values.container].payload / 1000);
    var answer = calculate(values);
    var invalid = answer.error || Object.values(controls).some(function (control) { return !control.checkValidity(); });
    Object.values(controls).forEach(function (control) { control.setAttribute('aria-invalid', String(!control.checkValidity())); });
    error.textContent = invalid ? (answer.error || 'Check the highlighted inputs and enter a value within the stated range.') : '';
    error.hidden = !invalid;
    results.hidden = !!invalid;
    if (invalid) return;
    output('cwi-res-sheets',answer.count.toLocaleString('en-IN'));
    output('cwi-res-cbm',answer.volume.toFixed(1)+' m³');
    output('cwi-res-wt',(answer.cargoMass/1000).toFixed(1)+' t');
    output('cwi-res-limit',answer.limit+' sets this estimate.');
    output('cwi-res-plan',answer.positions+' stack positions ('+answer.along+' along × '+answer.across+' across), up to '+answer.layers+' sheets high. '+answer.stackHeight.toLocaleString('en-IN')+' mm available for panels after the height allowance.');
    output('cwi-res-check','Weight ceiling: '+answer.weightCount.toLocaleString('en-IN')+' sheets. Layout ceiling: '+answer.layoutCount.toLocaleString('en-IN')+' sheets. Estimated panel mass: '+(answer.panelMass/1000).toFixed(1)+' t; packing allowance: '+values.packing.toLocaleString('en-IN')+' kg.');
    output('cwi-res-equipment','Equipment example: '+containers[values.container].length.toLocaleString('en-IN')+' × 2,352 × 2,395 mm inside; door 2,340 × 2,292 mm. Equipment payload ceiling '+(containers[values.container].payload/1000).toFixed(2)+' t. Your confirmed route limit may be lower.');
  }
  root.querySelector('fieldset').disabled = false;
  document.getElementById('cwi-calc-unavailable').hidden = true;
  root.addEventListener('input',update);
  root.addEventListener('change',update);
  update();
})();
