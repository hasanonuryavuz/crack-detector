const form = document.querySelector('#inspect-form');
const error = document.querySelector('#error');
let result = null;
let view = 'overlay';
document.querySelector('#image').addEventListener('change', event => {
  document.querySelector('#filename').textContent = event.target.files[0]?.name || 'JPEG / PNG · İstek sınırı 8 MB';
});
function showView(name) {
  view = name;
  if (!result) return;
  const source = 'data:image/png;base64,' + result.images[name];
  document.querySelector('#result-image').src = source;
  document.querySelector('#result-image').alt = {overlay:'Kusur adayları işaretlenmiş yüzey',edges:'Canny kenar haritası',original:'Analiz ölçeğinde orijinal görsel'}[name];
  document.querySelector('#download').href = source;
  document.querySelector('#download').download = 'surfacelab-' + name + '.png';
  document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('active', button.dataset.view === name));
}
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
async function inspect(endpoint) {
  if (!form.reportValidity()) return;
  const data = new FormData(form);
  error.hidden = true;
  document.querySelectorAll('button').forEach(button => button.disabled = true);
  document.querySelector('#state').textContent = 'İŞLENİYOR';
  try {
    const response = await fetch(endpoint, {method:'POST', body:data});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Analiz tamamlanamadı.');
    result = payload;
    document.querySelector('#empty').hidden = true;
    document.querySelector('#output').hidden = false;
    document.querySelector('#count').textContent = result.count;
    document.querySelector('#time').textContent = result.elapsed_ms + ' ms';
    document.querySelector('#density').textContent = '%' + result.edge_density_percent;
    const verdict = document.querySelector('#verdict');
    verdict.textContent = result.count ? 'İnceleme gerekli: ' + result.count + ' çatlak/çizik adayı işaretlendi.' : 'Bu ayarlarla aday iz bulunamadı. Bu, kusursuzluk garantisi değildir.';
    verdict.classList.toggle('review', result.count > 0);
    document.querySelector('#dimensions').textContent = result.input_size.join(' × ') + ' → ' + result.analysis_size.join(' × ') + ' px';
    const list = document.querySelector('#candidates');
    list.replaceChildren();
    if (result.count) {
      const table = document.createElement('table');
      const header = table.createTHead().insertRow();
      ['Aday','Uzunluk (px)','Uzunluk/en'].forEach(text => {const cell=document.createElement('th');cell.textContent=text;header.append(cell);});
      const body = table.createTBody();
      result.candidates.slice(0, 20).forEach((candidate, i) => {
        const row = body.insertRow();
        [i+1,candidate.length_px,candidate.elongation].forEach(value => row.insertCell().textContent = value);
      });
      list.append(table);
      if (result.count > 20) {const note=document.createElement('p');note.className='helper';note.textContent='En uzun 20 aday listeleniyor; tüm adaylar görselde işaretlidir.';list.append(note);}
    }
    showView('overlay');
    document.querySelector('#state').textContent = 'TAMAMLANDI';
  } catch (exc) {
    error.textContent = exc.message;
    error.hidden = false;
    document.querySelector('#state').textContent = 'HATA';
  } finally {
    document.querySelectorAll('button').forEach(button => button.disabled = false);
  }
}
form.addEventListener('submit', event => {event.preventDefault();inspect('/api/analyze');});
document.querySelectorAll('[data-demo]').forEach(button => button.addEventListener('click', () => inspect('/api/demo/' + button.dataset.demo)));
