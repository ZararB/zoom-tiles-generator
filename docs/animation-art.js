// Deterministic vector illustration. No map service, model, or external asset needed.
const canvas=document.getElementById('film'),ctx=canvas.getContext('2d');
const TAU=Math.PI*2;
const C={bg:'#000000',ink:'#ffffff',muted:'#a3a3a3',orange:'#f97316',secondary:'#dedede',line:'#333333',land:'#bdbdbd',water:'#525252',road:'#fafafa',dark:'#262626'};
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=v=>{v=clamp(v);return v*v*(3-2*v)};
const mix=(a,b,t)=>a+(b-a)*t;
function random(seed){let s=seed>>>0;return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296}}
function path(g,points,close=true){g.beginPath();points.forEach((p,i)=>i?g.lineTo(...p):g.moveTo(...p));if(close)g.closePath()}
function text(str,x,y,size=20,color=C.ink,weight=400,align='left'){ctx.fillStyle=color;ctx.font=`${weight} ${size}px "Segoe UI",sans-serif`;ctx.textAlign=align;ctx.fillText(str,x,y);ctx.textAlign='left'}
function line(a,b,color=C.line,width=1,dash=[]){ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.stroke();ctx.setLineDash([])}
function rounded(x,y,w,h,r=8){ctx.beginPath();ctx.roundRect(x,y,w,h,r)}
function makeTexture(level){
 const tex=document.createElement('canvas');tex.width=tex.height=1200;const g=tex.getContext('2d');g.scale(1200,1200);g.fillStyle=C.land;g.fillRect(0,0,1,1);const rng=random(991);
 // The same terrain, river and arterial road geometry is used at every level.
 for(let i=0;i<80;i++){let x=rng(),y=rng(),r=.025+rng()*.11;g.fillStyle=['#b3b3b3','#ababab','#c9c9c9','#b8b8b8'][i%4];g.beginPath();g.ellipse(x,y,r,r*.6,rng(),0,TAU);g.fill()}
 for(let i=0;i<26;i++){const x=.05+rng()*.9,y=.04+rng()*.9;if(Math.abs(x-(.25+y*.45))<.06)continue;g.fillStyle=i%2?'#9e9e9e':'#adadad';g.save();g.translate(x,y);g.rotate(-.15);g.fillRect(0,0,.04+rng()*.06,.025+rng()*.03);g.strokeStyle='#c5c5c5';g.lineWidth=.0015;g.strokeRect(0,0,.06,.04);g.restore()}
 g.beginPath();g.moveTo(.22,-.1);g.bezierCurveTo(.05,.16,.57,.17,.45,.40);g.bezierCurveTo(.32,.65,.9,.56,.76,1.1);g.lineWidth=.049;g.strokeStyle='#888888';g.stroke();g.lineWidth=.034;g.strokeStyle=C.water;g.stroke();g.lineWidth=.0015;g.strokeStyle='#737373';g.stroke();
 const road=(pts,width=.012)=>{path(g,pts,false);g.lineCap='round';g.lineJoin='round';g.strokeStyle='#797979';g.lineWidth=width+.004;g.stroke();g.strokeStyle=C.road;g.lineWidth=width;g.stroke()};
 road([[-.05,.70],[.17,.59],[.30,.55],[.46,.48],[.61,.47],[.76,.35],[1.06,.29]]);
 road([[.51,-.05],[.53,.15],[.61,.31],[.61,.47],[.58,.68],[.48,.83],[.46,1.05]],.009);
 // Existing bridge stays fixed across levels, independent of tile boundaries.
 g.fillStyle='#a45424';g.save();g.translate(.456,.484);g.rotate(-.42);g.fillRect(-.033,-.012,.066,.024);g.fillStyle='#e6e6e6';g.fillRect(-.033,-.007,.066,.014);g.restore();
 const trees=random(846);for(let i=0;i<225;i++){const x=trees(),y=trees();if((x<.27&&y<.44)||(x>.75&&y>.57)||(x>.67&&y<.15)){g.fillStyle='#747474';g.beginPath();g.arc(x,y,.005,0,TAU);g.fill();path(g,[[x,y-.009],[x-.006,y+.003],[x+.006,y+.003]]);g.fillStyle=i%3?'#555555':'#666666';g.fill()}}
 if(level>=1){
  for(let i=0;i<6;i++){const y=.36+i*.039;road([[.48,y],[.65,y+.006]],.0033)}
  for(let i=0;i<5;i++){const x=.49+i*.034;road([[x,.35],[x+.006,.58]],.0033)}
  const buildings=random(47);for(let r=0;r<6;r++)for(let c=0;c<5;c++){if(level===1&&(r+c)%3)continue;const x=.486+c*.034,y=.365+r*.037;g.save();g.translate(x,y);g.rotate((buildings()-.5)*.15);g.fillStyle='#686868';g.fillRect(0,0,.015,.012);g.fillStyle=(r+c)%3?'#f8ab73':'#ab4c0f';g.fillRect(.001,-.002,.014,.01);g.strokeStyle='#71320a';g.lineWidth=.001;path(g,[[.001,.003],[.015,.003]],false);g.stroke();if(level>=2){g.fillStyle='#a6a6a6';g.fillRect(.003,.013,.012,.006)}g.restore()}
 }
 if(level>=2){const rng2=random(122);for(let i=0;i<65;i++){const x=.34+rng2()*.38,y=.24+rng2()*.48;if(Math.abs(x-(.48+y*.1))>.12)continue;g.fillStyle='#dc9568';g.fillRect(x,y,.009,.007);g.strokeStyle='#777777';g.lineWidth=.001;g.strokeRect(x-.002,y-.002,.013,.011)}
  g.fillStyle='#ffb680';g.fillRect(.557,.44,.023,.019);g.fillStyle='#c05213';g.fillRect(.559,.437,.019,.013);g.fillStyle='#8a3f14';g.beginPath();g.arc(.57,.44,.004,0,TAU);g.fill()
 }
 return tex;
}
const textures=[makeTexture(0),makeTexture(1),makeTexture(2)];
function projection(view,x,y,h=0){return [view.x+(x-y)*view.s*.866,view.y+(x+y)*view.s*(view.tilt??.46)-h]}
function corners(view,b,h=0){const [x,y,w,d]=b;return[[x,y],[x+w,y],[x+w,y+d],[x,y+d]].map(p=>projection(view,...p,h))}
function tile(view,b,level=1,{raise=0,gap=0,alpha=1,outline=null,world=[0,0,1,1],reveal=1}={}){
 const [x,y,w,h]=b,center=projection(view,x+w/2,y+h/2),offset=[(x+w/2-.5)*gap,(y+h/2-.5)*gap];
 const v={...view,x:view.x+offset[0],y:view.y+offset[1]};const points=corners(v,b,raise);
 ctx.save();ctx.globalAlpha=alpha;
 // Extruded front and right edges give the diagram a physical tile structure.
 path(ctx,[points[1],points[2],[points[2][0],points[2][1]+10],[points[1][0],points[1][1]+10]]);ctx.fillStyle='#676767';ctx.fill();
 path(ctx,[points[2],points[3],[points[3][0],points[3][1]+10],[points[2][0],points[2][1]+10]]);ctx.fillStyle='#404040';ctx.fill();
 path(ctx,points);ctx.fillStyle='#1a1a1a';ctx.fill();ctx.save();ctx.clip();
 ctx.transform(v.s*.866,v.s*(v.tilt??.46),-v.s*.866,v.s*(v.tilt??.46),v.x,v.y-raise);
 const [wx,wy,ww,wh]=world;
 if(reveal<1){ctx.fillStyle='#333333';ctx.fillRect(x,y,w,h);ctx.beginPath();ctx.rect(x,y,w*reveal,h);ctx.clip()}
 ctx.drawImage(textures[level],(wx+x*ww)*1200,(wy+y*wh)*1200,w*ww*1200,h*wh*1200,x,y,w,h);
 ctx.restore();path(ctx,points);ctx.lineWidth=outline?3:1;ctx.strokeStyle=outline||'#ffffff50';ctx.stroke();
 ctx.restore();return {points,center:projection(v,x+w/2,y+h/2,raise)};
}
function grid(view,n,level,options={}){let cells=[];for(let y=0;y<n;y++)for(let x=0;x<n;x++)cells.push({x,y});cells.sort((a,b)=>(a.x+a.y)-(b.x+b.y));for(const {x,y}of cells)tile(view,[x/n,y/n,1/n,1/n],level,{...options,raise:(options.raise||0)+(options.wave||0)*Math.sin(x*.8+y*.6),outline:options.highlight&&x===options.highlight[0]&&y===options.highlight[1]?C.orange:null})}
function arc(a,b,p,color=C.secondary){const control=[(a[0]+b[0])/2,(a[1]+b[1])/2-85];ctx.beginPath();ctx.moveTo(...a);ctx.quadraticCurveTo(...control,...b);ctx.strokeStyle=color+'80';ctx.lineWidth=2;ctx.setLineDash([5,8]);ctx.stroke();ctx.setLineDash([]);for(let k=0;k<2;k++){const t=(p+k*.5)%1,q=1-t;const x=q*q*a[0]+2*q*t*control[0]+t*t*b[0],y=q*q*a[1]+2*q*t*control[1]+t*t*b[1];ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,3.5,0,TAU);ctx.fill()}}
function label(str,x,y,color=C.muted){text(str,x,y,16,color,500)}

export {canvas,ctx,C,textures,clamp,ease,mix,text,line,path,rounded,label,projection,corners,tile,grid,arc};
