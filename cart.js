/* Local-only shopping cart. Quantities describe recipe needs, not retail pack sizes. */
var cart = {}, bought = {}, cartToastTimer;
var CART_KEY = 'cv_cart_v1';
function recipeByName(name){ return R.find(function(r){ return r[0] === name; }); }
function escapeCart(value){ return String(value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
function parseMaterial(raw){
  var optional = /[（(]可选[）)]/.test(raw);
  var text = raw.replace(/[（(]可选[）)]/g,'').trim();
  if(text === '冰杯' || text === '便利店冰杯'){return {name:'冰杯',quantity:1,unit:'个',optional:optional};}
  var m = text.match(/^(.*?)\s*(\d+(?:\.\d+)?(?:\s*[-–~至]\s*\d+(?:\.\d+)?)?|半)\s*(ml|毫升|g|克|瓶|罐|个|颗|片|勺|茶匙|支|块)$/i);
  if(!m || !m[1].trim()){return {name:text,quantity:null,unit:'',optional:optional};}
  var amount=m[2], range=/[-–~至]/.test(amount);
  return {name:m[1].trim(),quantity:range?null:(amount==='半'?0.5:Number(amount)),unit:m[3].toLowerCase().replace('毫升','ml').replace('克','g'),range:range?amount:'',optional:optional};
}
function shoppingList(){
  var groups = new Map();
  R.forEach(function(recipe){
    var cups=cart[recipe[0]];
    if(!cups){return;}
    recipe[3].forEach(function(raw){
      raw.split('、').forEach(function(part){
        var material=parseMaterial(part);
        var key=JSON.stringify([material.name,material.unit,material.optional,material.range||'']);
        if(!groups.has(key)){groups.set(key,{key:key,name:material.name,unit:material.unit,optional:material.optional,range:material.range||'',quantity:material.quantity===null?null:0,cups:0,sources:[]});}
        var row=groups.get(key);
        if(row.quantity!==null){row.quantity+=material.quantity*cups;}
        row.cups+=cups;row.sources.push(recipe[0]+' × '+cups);
      });
    });
  });
  return Array.from(groups.values()).map(function(row){
    row.amount=row.range?row.range+row.unit+' × '+row.cups+' 份':(row.quantity===null?'适量':Number(row.quantity.toFixed(2))+' '+row.unit);
    row.signature=JSON.stringify([row.quantity,row.cups]);
    return row;
  });
}
function saveCart(){
  var active={};
  shoppingList().forEach(function(row){if(bought[row.key]===row.signature){active[row.key]=row.signature;}});
  bought=active;
  try{localStorage.setItem(CART_KEY,JSON.stringify({cart:cart,bought:bought}));}catch(e){cartToast('当前浏览器无法保存，购物车仅保留在本次页面中');}
  updateCartCount();
}
function updateCartCount(){
  var total=Object.keys(cart).reduce(function(n,k){return n+cart[k];},0);
  document.getElementById('cartCount').textContent=total;
  document.getElementById('cartBtn').setAttribute('aria-label','查看购物车，共 '+total+' 杯');
}
function cartToast(message){
  clearTimeout(cartToastTimer);document.getElementById('cartToast').textContent=message;
  cartToastTimer=setTimeout(function(){document.getElementById('cartToast').textContent='';},2200);
}
function addToCart(name){
  if(!recipeByName(name)){return;}
  if((cart[name]||0)>=99){cartToast('每款最多添加 99 杯');return;}
  cart[name]=(cart[name]||0)+1;
  cartToast('已加入 '+name+' · '+cart[name]+' 杯');saveCart();
}
function renderCart(){
  var rows=shoppingList(), names=R.filter(function(r){return cart[r[0]];});
  var total=names.reduce(function(n,r){return n+cart[r[0]];},0);
  var done=rows.filter(function(r){return bought[r.key]===r.signature;}).length;
  var html='<div class="cart-head"><h3 id="cartTitle">购物车</h3><button class="cart-close" data-cart-close>关闭</button></div>';
  if(!names.length){
    html+='<div class="cart-empty">还没有想调的饮品<br><small>选一杯加入，就能生成采购清单。</small></div><div class="sheet-actions"><button class="pri" data-cart-close>去挑选饮品</button></div>';
  }else{
    html+='<div class="cart-toolbar"><p class="cart-summary">'+names.length+' 款饮品 · '+total+' 杯</p><button class="cart-clear" data-cart-clear>清空购物车</button></div>';
    names.forEach(function(r){
      var n=escapeCart(r[0]);
      html+='<div class="cart-row">'+drinkArt(r[0])+'<div class="cart-name">'+n+'<button class="cart-remove" data-cart-remove="'+n+'" aria-label="移除'+n+'">移除</button></div><div class="cart-qty"><button data-cart-delta="-1" data-cart-name="'+n+'" aria-label="'+n+'减少一杯"'+(cart[r[0]]===1?' disabled':'')+'>−</button><output aria-label="杯数">'+cart[r[0]]+'</output><button data-cart-delta="1" data-cart-name="'+n+'" aria-label="'+n+'增加一杯"'+(cart[r[0]]===99?' disabled':'')+'>＋</button></div></div>';
    });
    html+='<h4>采购清单 · 已买 '+done+' / '+rows.length+'</h4><p class="cart-summary">数量为所选杯数的配方用量，按商品包装购买；未标用量的材料按需准备。</p><div class="buy-list">';
    rows.forEach(function(row){
      var checked=bought[row.key]===row.signature;
      html+='<label class="buy-item'+(checked?' done':'')+'"><input type="checkbox" data-buy-key="'+escapeCart(row.key)+'"'+(checked?' checked':'')+' aria-label="'+escapeCart(row.name+' '+row.amount)+'已买"><span>'+escapeCart(row.name)+(row.optional?'（可选）':'')+'<small>'+escapeCart(row.sources.join('、'))+'</small></span><b>'+escapeCart(row.amount)+'</b></label>';
    });
    html+='</div>';
  }
  document.getElementById('sheetBody').innerHTML=html;
}
function openCart(){
  curName=null;sheet.classList.add('cart-open');sheet.setAttribute('aria-label','购物车与采购清单');renderCart();
  sheet.classList.add('on');bd.classList.add('on');document.body.classList.add('lock');sheet.scrollTop=0;
  sheet.querySelector('[data-cart-close]').focus({preventScroll:true});
}
try{
  var saved=JSON.parse(localStorage.getItem(CART_KEY)||'{}');
  if(saved && saved.cart && typeof saved.cart==='object'){
    R.forEach(function(r){var n=saved.cart[r[0]];if(Number.isInteger(n)&&n>0&&n<=99){cart[r[0]]=n;}});
  }
  if(saved && saved.bought && typeof saved.bought==='object'){
    shoppingList().forEach(function(row){if(saved.bought[row.key]===row.signature){bought[row.key]=row.signature;}});
  }
}catch(e){/* A malformed or unavailable local store starts with an empty cart. */}
document.getElementById('cartBtn').addEventListener('click',openCart);
document.getElementById('sheetBody').addEventListener('click',function(e){
  if(!sheet.classList.contains('cart-open')){return;}
  if(e.target.closest('[data-cart-close]')){closeSheet();document.getElementById('cartBtn').focus();return;}
  if(e.target.closest('[data-cart-clear]')){
    cart={};bought={};saveCart();renderCart();sheet.scrollTop=0;
    sheet.querySelector('[data-cart-close]').focus({preventScroll:true});
    return;
  }
  var remove=e.target.closest('[data-cart-remove]'), delta=e.target.closest('[data-cart-delta]');
  if(!remove&&!delta){return;}
  var name=remove?remove.getAttribute('data-cart-remove'):delta.getAttribute('data-cart-name');
  if(remove){delete cart[name];}else{cart[name]=Math.max(1,Math.min(99,cart[name]+Number(delta.getAttribute('data-cart-delta'))));}
  var top=sheet.scrollTop;saveCart();renderCart();sheet.scrollTop=top;
  var next=delta?Array.from(sheet.querySelectorAll('[data-cart-delta]')).find(function(b){return b.getAttribute('data-cart-name')===name&&b.getAttribute('data-cart-delta')===delta.getAttribute('data-cart-delta')&&!b.disabled;}):null;
  (next||sheet.querySelector('[data-cart-close]')).focus({preventScroll:true});
});
document.getElementById('sheetBody').addEventListener('change',function(e){
  var input=e.target.closest('[data-buy-key]');if(!input){return;}
  var key=input.getAttribute('data-buy-key'), row=shoppingList().find(function(r){return r.key===key;});
  if(!row){return;}
  if(input.checked){bought[key]=row.signature;}else{delete bought[key];}
  saveCart();input.closest('.buy-item').classList.toggle('done',input.checked);
  var rows=shoppingList();sheet.querySelector('h4').textContent='采购清单 · 已买 '+rows.filter(function(r){return bought[r.key]===r.signature;}).length+' / '+rows.length;
});
document.addEventListener('keydown',function(e){
  if(!sheet.classList.contains('cart-open')||!sheet.classList.contains('on')){return;}
  if(e.key==='Escape'){closeSheet();document.getElementById('cartBtn').focus();}
  if(e.key==='Tab'){
    var controls=Array.from(sheet.querySelectorAll('button:not(:disabled),input'));
    var first=controls[0],last=controls[controls.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  }
});
updateCartCount();
