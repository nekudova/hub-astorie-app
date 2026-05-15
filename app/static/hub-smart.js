(function(){
  function debounce(fn, delay){let t=null; return function(){const a=arguments; clearTimeout(t); t=setTimeout(()=>fn.apply(null,a), delay||220);};}
  function clearSuggestions(){document.querySelectorAll('.smart-suggestions').forEach(el=>{el.innerHTML=''; el.style.display='none';});}
  window.HubSmart={
    initPartnerAutocomplete:function(inputSelector,opt){
      opt=opt||{}; const input=document.querySelector(inputSelector); if(!input) return;
      const hidden=opt.hiddenSelector?document.querySelector(opt.hiddenSelector):null;
      const info=opt.infoSelector?document.querySelector(opt.infoSelector):null;
      const box=document.createElement('div'); box.className='smart-suggestions'; input.parentNode.appendChild(box);
      const search=debounce(async function(){
        const q=input.value.trim(); if(q.length<2){box.innerHTML=''; box.style.display='none'; return;}
        box.style.display='block'; box.innerHTML='<div class="smart-suggestion muted">Načítám…</div>';
        try{
          const res=await fetch('/api/partners/search?q='+encodeURIComponent(q)+'&limit=20'); const data=await res.json();
          if(!data.ok || !data.items || !data.items.length){box.innerHTML='<div class="smart-suggestion muted">Nenalezen žádný partner.</div>'; return;}
          box.innerHTML=data.items.map((it,i)=>`<button type="button" class="smart-suggestion" data-i="${i}" data-code="${it.partner_code}"><strong>${it.label||it.name||it.partner_code}</strong><span>IČO: ${it.ico||'—'} · DS: ${it.data_box||'—'} · ${it.city||''}</span></button>`).join('');
          box.querySelectorAll('button.smart-suggestion').forEach(btn=>btn.onclick=async()=>{
            const code=btn.dataset.code; if(hidden){hidden.value=code; input.value=btn.querySelector('strong').textContent;} else {input.value=code;}
            box.innerHTML=''; box.style.display='none';
            if(info){ info.innerHTML='Načítám detail partnera…'; try{ const r=await fetch('/api/partners/'+encodeURIComponent(code)+'/form-source'); const d=await r.json(); if(d.ok){const p=d.partner; info.innerHTML=`<strong>${p.name||''}</strong><br>IČO: ${p.ico||''}<br>DS: ${p.data_box||''}<br>E-mail: ${p.registry_email||''}<br>Adresa: ${p.address_full||''}`;}}catch(e){info.innerHTML='Detail partnera se nepodařilo načíst.';} }
          });
        } catch(e){ box.innerHTML='<div class="smart-suggestion error">Technická chyba vyhledávání.</div>'; }
      },220);
      input.addEventListener('input',search); input.addEventListener('focus',search);
      input.addEventListener('keydown',function(e){const items=[...box.querySelectorAll('button.smart-suggestion')]; if(!items.length)return; let i=items.findIndex(x=>x.classList.contains('selected')); if(e.key==='ArrowDown'){e.preventDefault(); if(i>=0)items[i].classList.remove('selected'); i=i+1>=items.length?0:i+1; items[i].classList.add('selected'); items[i].scrollIntoView({block:'nearest'});} if(e.key==='ArrowUp'){e.preventDefault(); if(i>=0)items[i].classList.remove('selected'); i=i<=0?items.length-1:i-1; items[i].classList.add('selected'); items[i].scrollIntoView({block:'nearest'});} if(e.key==='Enter'&&i>=0){e.preventDefault(); items[i].click();} if(e.key==='Escape') clearSuggestions();});
      document.addEventListener('click',e=>{if(!box.contains(e.target)&&e.target!==input) clearSuggestions();});
    },
    initTableFilter:function(inputSelector,tableSelector){const input=document.querySelector(inputSelector), table=document.querySelector(tableSelector); if(!input||!table)return; input.addEventListener('input',debounce(()=>{const q=input.value.toLowerCase().trim(); table.querySelectorAll('tbody tr').forEach(tr=>{tr.style.display=(!q||tr.innerText.toLowerCase().includes(q))?'':'none';});},80));}
  };
})();
