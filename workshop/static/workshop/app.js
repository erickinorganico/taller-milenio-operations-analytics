document.querySelectorAll('form').forEach(form=>{form.addEventListener('submit',event=>{if(form.dataset.confirm&&!window.confirm(form.dataset.confirm)){event.preventDefault();return;}const button=event.submitter;if(button){setTimeout(()=>{button.disabled=true;button.dataset.label=button.textContent;button.textContent=form.method.toLowerCase()==='get'?'Aplicando…':'Guardando…';},0);}});});
document.querySelectorAll('nav a').forEach(link=>{if(link.getAttribute('href')===location.pathname)link.setAttribute('aria-current','page');});

document.querySelectorAll("[data-print]").forEach(button=>button.addEventListener("click",()=>window.print()));
