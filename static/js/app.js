(() => {
  const text = document.querySelector('#description');
  const category = document.querySelector('#category');
  const recommendation = document.querySelector('#recommendation');
  const estimate = document.querySelector('#estimate');
  if (!text || !category) return;
  const rules = {
    Plumbing: { base: 450, words: ['leak','tap','pipe','drain','plumb','water','toilet'] },
    Electrical: { base: 500, words: ['electric','wire','light','switch','power','fan','socket'] },
    Cleaning: { base: 350, words: ['clean','dust','kitchen','bathroom'] },
    Carpentry: { base: 550, words: ['wood','door','cabinet','furniture','carpenter','shelf'] },
    'Appliance Repair': { base: 600, words: ['fridge','washer','washing machine','ac','appliance','oven','machine'] }
  };
  function update() {
    const value = text.value.toLowerCase();
    const ranked = Object.entries(rules).map(([name, rule]) => [rule.words.filter(word => value.includes(word)).length, name]);
    const [score, best] = ranked.sort((a,b) => b[0]-a[0])[0];
    const chosen = category.value || (score ? best : '');
    recommendation.textContent = score ? `Suggested service: ${best}${category.value ? ' · your selection: '+category.value : ''}` : 'Describe the issue to get a service suggestion.';
    const words = text.value.trim().split(/\s+/).filter(Boolean).length;
    estimate.textContent = chosen ? `₹${rules[chosen].base + Math.min(1000,Math.max(0,words-8)*25)}` : '₹—';
  }
  text.addEventListener('input', update); category.addEventListener('change', update); update();
})();
