#!/usr/bin/env python3
"""Web UI for the KALX playlist scraper."""

import json
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template_string, request

from db import get_connection, get_all_tags, get_db_stats, get_playlist_from_db, get_top_artists, search_db
from kalx import fetch, fetch_playlist, SPINITRON_BASE, STATIONS

app = Flask(__name__)

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bay Area Radio Play Log</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#241848;color:#e8e0f0;min-height:100vh}
header{background:#332060;border-bottom:2px solid #e060a0;padding:.8rem 1.2rem;display:flex;align-items:center;justify-content:space-between}
header h1{font-size:1.2rem;font-weight:700;letter-spacing:-.02em;color:#f5f0f8}
header h1 span{color:#e060a0}
.filter-toggle{display:none;background:none;border:1px solid #5c3d7a;color:#c8a0c8;padding:.4rem .8rem;border-radius:4px;font-size:.8rem;cursor:pointer}
.filter-toggle:hover{border-color:#e060a0;color:#e060a0}
.backfill-banner{background:#332060;border-bottom:1px solid #5a3d7a;padding:.5rem 1.2rem;font-size:.78rem;color:#c8a0c8;display:flex;align-items:center;gap:.5rem}
.backfill-banner .spinner{width:12px;height:12px;border-width:2px}
.backfill-banner strong{color:#e060a0}
.backfill-banner.done{background:#2d1a50;color:#7a6090}

/* Layout */
.app{display:flex;min-height:calc(100vh - 52px)}
.sidebar{width:220px;flex-shrink:0;background:#2d1a50;border-right:1px solid #4a3870;padding:1rem;overflow-y:auto;max-height:calc(100vh - 52px);position:sticky;top:0}
.main{flex:1;min-width:0;padding:1rem 1.5rem}

/* Sidebar filter panels */
.filter-section{margin-bottom:1.2rem}
.filter-title{font-size:.7rem;color:#9a80b0;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.5rem;font-weight:600}
.filter-list{display:flex;flex-direction:column;gap:.15rem;max-height:200px;overflow-y:auto}
.filter-list.short{max-height:none}
.filter-item{display:flex;align-items:center;gap:.4rem;padding:.2rem .3rem;border-radius:3px;cursor:pointer;font-size:.8rem;color:#a090b8;user-select:none}
.filter-item:hover{background:#332060;color:#e8e0f0}
.filter-item input{accent-color:#e060a0;margin:0;cursor:pointer}
.filter-item.checked{color:#e8e0f0}
.filter-count{color:#7a6090;font-size:.7rem;margin-left:auto}
.genre-search{width:100%;background:#241848;border:1px solid #4a3870;border-radius:3px;color:#c8a0c8;padding:.3rem .5rem;font-size:.78rem;margin-bottom:.4rem}
.genre-search:focus{outline:none;border-color:#e060a0}

/* Search bar */
.search-bar{display:flex;gap:.5rem;margin-bottom:1rem;align-items:stretch}
.search-bar input{flex:1;background:#332060;border:1px solid #5a3d7a;border-radius:6px;color:#e8e0f0;padding:.5rem .8rem;font-size:.9rem;min-width:0}
.search-bar input:focus{outline:none;border-color:#e060a0}
.search-bar input::placeholder{color:#7a6090}
.search-bar select{background:#332060;border:1px solid #5a3d7a;border-radius:6px;color:#e8e0f0;padding:.5rem;font-size:.82rem}
.search-bar button{background:#e060a0;color:#fff;border:none;border-radius:6px;padding:.5rem 1rem;font-size:.9rem;font-weight:600;cursor:pointer;white-space:nowrap}
.search-bar button:hover{background:#c84888}
.search-bar button:disabled{background:#5a3d7a;cursor:wait;color:#9a80b0}

/* Tabs */
.tabs{display:flex;gap:0;margin-bottom:1rem}
.tab{padding:.45rem 1rem;background:#332060;border:1px solid #5a3d7a;color:#9a80b0;cursor:pointer;font-size:.8rem;font-weight:500}
.tab:first-child{border-radius:5px 0 0 5px}
.tab:last-child{border-radius:0 5px 5px 0}
.tab.active{background:#e060a0;color:#fff;border-color:#e060a0}

/* Content */
.status{color:#9a80b0;font-size:.85rem;padding:.6rem 0}
.status.error{color:#e88080}
.empty{color:#7a6090;padding:2rem;text-align:center}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #5a3d7a;border-top-color:#e060a0;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:.4rem}
@keyframes spin{to{transform:rotate(360deg)}}

/* Table */
.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:.82rem}
th{text-align:left;padding:.45rem .6rem;border-bottom:2px solid #4a3870;color:#9a80b0;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
td{padding:.45rem .6rem;border-bottom:1px solid #2b2054;white-space:nowrap}
td.wrap{white-space:normal}
tr:hover td{background:#332060}
.artist-name{color:#e060a0;font-weight:500}
.song-name{color:#e8e0f0}
.meta{color:#7a6090}
.dj-name{color:#c8a0c8}
.playlist-link{color:#c8a0c8;text-decoration:none;cursor:pointer}
.playlist-link:hover{text-decoration:underline;color:#e8b8c8}
.rank{color:#e060a0;font-weight:700;text-align:right}
.plays{font-variant-numeric:tabular-nums}
.station-tags{display:flex;gap:.2rem;flex-wrap:wrap}
.station-tag{font-size:.65rem;padding:.1rem .35rem;border-radius:3px;background:#332060;color:#a090b8;border:1px solid #4a3870}
.year-tag{color:#7a6090;font-size:.7rem;margin-left:.3rem}
.showbill-header{margin-bottom:1rem;color:#9a80b0;font-size:.85rem}
.showbill-header strong{color:#e060a0}
.rec-score{color:#e060a0;font-weight:700;font-variant-numeric:tabular-nums}
.venue-badge{display:inline-block;font-size:.6rem;padding:.1rem .35rem;border-radius:3px;background:#4a3870;color:#c8a0c8;font-weight:600;margin-left:.35rem;vertical-align:middle}
.rec-city{color:#c8a0c8;font-size:.75rem}
.rec-signals{font-size:.7rem;color:#7a6090}
.showbill-input{display:flex;gap:.5rem;margin-bottom:1rem}
.showbill-input input{flex:1;background:#332060;border:1px solid #5a3d7a;border-radius:6px;color:#e8e0f0;padding:.5rem .8rem;font-size:.9rem}
.showbill-input input:focus{outline:none;border-color:#e060a0}
.showbill-input input::placeholder{color:#7a6090}
.showbill-input button{background:#e060a0;color:#fff;border:none;border-radius:6px;padding:.5rem 1rem;font-weight:600;cursor:pointer}
.showbill-input button:hover{background:#c84888}
.local-badge{display:inline-block;font-size:.6rem;padding:.1rem .35rem;border-radius:3px;background:#5a7a50;color:#c8e8c0;font-weight:600;margin-left:.35rem;vertical-align:middle;letter-spacing:.02em}
.toggle-row{display:flex;align-items:center;justify-content:space-between;padding:.3rem 0}
.toggle-label{font-size:.8rem;color:#a090b8}
.toggle{position:relative;width:36px;height:20px;cursor:pointer}
.toggle input{opacity:0;width:0;height:0}
.toggle-track{position:absolute;inset:0;background:#5a3d7a;border-radius:10px;transition:background .2s}
.toggle input:checked+.toggle-track{background:#5a7a50}
.toggle-knob{position:absolute;top:2px;left:2px;width:16px;height:16px;background:#e8e0f0;border-radius:50%;transition:transform .2s}
.toggle input:checked~.toggle-knob{transform:translateX(16px)}
.back-link{color:#c8a0c8;cursor:pointer;font-size:.85rem;margin-bottom:.8rem;display:inline-block}
.back-link:hover{text-decoration:underline;color:#e8b8c8}
.playlist-header{margin-bottom:.8rem}
.playlist-header h2{font-size:1.1rem;margin-bottom:.2rem;color:#f5f0f8}
.playlist-header .details{color:#a090b8;font-size:.85rem}

/* Music links */
.music-links{display:inline;margin-left:.4rem;font-size:.7rem;color:#7a6090}
.music-links a{color:#9a80b0;text-decoration:none;transition:color .15s}
.music-links a:hover{color:#e060a0;text-decoration:underline}
.music-links .sep{color:#5a3d7a}

/* Mobile */
@media(max-width:768px){
  .filter-toggle{display:block}
  .app{flex-direction:column}
  .sidebar{width:100%;max-height:60vh;overflow-y:auto;position:static;border-right:none;border-bottom:1px solid #4a3870;padding:.8rem;display:none}
  .sidebar.open{display:block}
  .sidebar .filter-panels{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
  .main{padding:.8rem}
  .search-bar{flex-wrap:wrap}
  .search-bar input{min-width:100%;font-size:16px}
  .search-bar button{width:100%}
  .tabs{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .tab{padding:.5rem .8rem;flex-shrink:0}
  td{font-size:.75rem;padding:.4rem}
  .filter-item{padding:.35rem .3rem}
  .music-links{display:block;margin-left:0;margin-top:.2rem}
  .hide-mobile{display:none}
}
@media(max-width:480px){
  .sidebar .filter-panels{grid-template-columns:1fr}
  header h1{font-size:.95rem}
  header{padding:.6rem .8rem}
  .main{padding:.5rem}
}
</style>
</head>
<body>
<header>
  <h1><span>Bay Area</span> Radio Play Log</h1>
  <button class="filter-toggle" onclick="toggleSidebar()">Filters</button>
</header>
<div class="backfill-banner" id="backfillBanner" style="display:none"></div>
<div class="app">
  <aside class="sidebar" id="sidebar">
    <div class="filter-panels">
      <div class="filter-section">
        <div class="filter-title">Stations</div>
        <div class="filter-list short" id="stationFilters"></div>
      </div>
      <div class="filter-section">
        <div class="toggle-row">
          <span class="toggle-label">Bay Area Local</span>
          <label class="toggle"><input type="checkbox" id="localToggle"><span class="toggle-track"></span><span class="toggle-knob"></span></label>
        </div>
      </div>
      <div class="filter-section">
        <div class="filter-title">Time Range</div>
        <div class="filter-list short" id="rangeFilters">
          <label class="filter-item"><input type="radio" name="range" value="1"> 24 hours</label>
          <label class="filter-item"><input type="radio" name="range" value="3"> 3 days</label>
          <label class="filter-item checked"><input type="radio" name="range" value="7" checked> 7 days</label>
          <label class="filter-item"><input type="radio" name="range" value="14"> 2 weeks</label>
          <label class="filter-item"><input type="radio" name="range" value="30"> 30 days</label>
          <label class="filter-item"><input type="radio" name="range" value="90"> 3 months</label>
          <label class="filter-item"><input type="radio" name="range" value="180"> 6 months</label>
        </div>
      </div>
      <div class="filter-section">
        <div class="filter-title">Release Era</div>
        <div class="filter-list short" id="eraFilters">
          <label class="filter-item"><input type="checkbox" name="era" value="2026-2026"> 2026</label>
          <label class="filter-item"><input type="checkbox" name="era" value="2025-2025"> 2025</label>
          <label class="filter-item"><input type="checkbox" name="era" value="2020-2024"> 2020s</label>
          <label class="filter-item"><input type="checkbox" name="era" value="2010-2019"> 2010s</label>
          <label class="filter-item"><input type="checkbox" name="era" value="2000-2009"> 2000s</label>
          <label class="filter-item"><input type="checkbox" name="era" value="1990-1999"> 90s</label>
          <label class="filter-item"><input type="checkbox" name="era" value="1980-1989"> 80s</label>
          <label class="filter-item"><input type="checkbox" name="era" value="1970-1979"> 70s</label>
          <label class="filter-item"><input type="checkbox" name="era" value="1960-1969"> 60s</label>
          <label class="filter-item"><input type="checkbox" name="era" value="1-1959"> Pre-60s</label>
        </div>
      </div>
      <div class="filter-section">
        <div class="filter-title">Genres</div>
        <input type="text" class="genre-search" id="genreSearch" placeholder="Filter genres...">
        <div class="filter-list" id="genreFilters"></div>
      </div>
    </div>
  </aside>
  <div class="main">
    <form id="searchForm" class="search-bar">
      <input type="text" id="artist" placeholder="Search for an artist..." autofocus>
      <button type="submit" id="searchBtn">Search</button>
    </form>
    <div class="tabs">
      <div class="tab" data-tab="results">Search</div>
      <div class="tab active" data-tab="leaderboard">Top Artists</div>
      <div class="tab" data-tab="showbill">Show Bill</div>
      <div class="tab" data-tab="recent">Recent</div>
    </div>
    <div id="content"></div>
  </div>
</div>

<script>
const $=s=>document.querySelector(s);
const $$=s=>document.querySelectorAll(s);
let currentTab='leaderboard';

function toggleSidebar(){$('#sidebar').classList.toggle('open')}

function getSelectedStations(){
  return [...$$('#stationFilters input:checked')].map(c=>c.value);
}
function getSelectedGenres(){
  return [...$$('#genreFilters input:checked')].map(c=>c.value);
}
function getSelectedEras(){
  return [...$$('#eraFilters input:checked')].map(c=>c.value);
}
function getYearRange(){
  const eras=getSelectedEras();
  if(!eras.length) return {};
  let min=9999, max=0;
  eras.forEach(e=>{const[a,b]=e.split('-').map(Number);if(a<min)min=a;if(b>max)max=b});
  return {year_min:min, year_max:max};
}
function getDays(){
  const r=$('input[name="range"]:checked');
  return r?r.value:'7';
}

// Highlight checked filter items
document.addEventListener('change',e=>{
  if(e.target.closest('.filter-item')){
    const item=e.target.closest('.filter-item');
    if(e.target.type==='checkbox') item.classList.toggle('checked',e.target.checked);
    if(e.target.type==='radio'){
      item.closest('.filter-list').querySelectorAll('.filter-item').forEach(fi=>fi.classList.remove('checked'));
      item.classList.add('checked');
    }
    if(currentTab==='leaderboard') loadLeaderboard();
  }
  if(e.target.id==='localToggle' && currentTab==='leaderboard') loadLeaderboard();
});

// Load stations
fetch('/api/stats').then(r=>r.json()).then(data=>{
  const el=$('#stationFilters');
  (data.stations||[]).forEach(s=>{
    const item=document.createElement('label');
    item.className='filter-item checked';
    item.innerHTML=`<input type="checkbox" value="${s}" checked> ${s}`;
    el.appendChild(item);
  });
});

// Load genres
fetch('/api/tags').then(r=>r.json()).then(data=>{
  window._allGenres=data;
  renderGenres(data);
});
function renderGenres(tags){
  const el=$('#genreFilters');
  const prev=getSelectedGenres();
  el.innerHTML='';
  tags.slice(0,80).forEach(t=>{
    const checked=prev.includes(t.tag);
    const item=document.createElement('label');
    item.className='filter-item'+(checked?' checked':'');
    item.innerHTML=`<input type="checkbox" value="${t.tag}"${checked?' checked':''}> ${t.tag} <span class="filter-count">${t.count}</span>`;
    el.appendChild(item);
  });
}
$('#genreSearch').addEventListener('input',e=>{
  const q=e.target.value.toLowerCase();
  const filtered=(window._allGenres||[]).filter(t=>t.tag.includes(q));
  renderGenres(filtered);
});

// Backfill status polling
function checkBackfill(){
  fetch('/api/backfill-status').then(r=>r.json()).then(s=>{
    const b=$('#backfillBanner');
    if(s.running){
      b.style.display='flex';
      b.className='backfill-banner';
      if(s.phase==='playlists'){
        b.innerHTML=`<span class="spinner"></span>Loading data: day <strong>${s.days_done||0}/${s.days_total||'?'}</strong> &middot; ${s.current_station||''} ${s.station_progress||''} &middot; <strong>${(s.playlists_fetched||0).toLocaleString()}</strong> playlists fetched${s.errors?` &middot; ${s.errors} errors`:''}`;
      }else if(s.phase==='tagging'){
        b.innerHTML=`<span class="spinner"></span>Tagging artists: <strong>${s.artists_tagged||0}/${s.artists_total||'?'}</strong>`;
      }
      setTimeout(checkBackfill,5000);
    }else if(s.phase==='done'){
      b.style.display='flex';
      b.className='backfill-banner done';
      b.innerHTML=`Data loaded: <strong>${(s.playlists_fetched||0).toLocaleString()}</strong> playlists in ${Math.round((s.elapsed_seconds||0)/60)}min`;
      setTimeout(()=>{b.style.display='none'},15000);
    }else if(s.phase==='error'){
      b.style.display='flex';
      b.className='backfill-banner';
      b.innerHTML=`<span style="color:#e88080">Backfill error</span>`;
    }else{
      b.style.display='none';
    }
  }).catch(()=>{});
}
checkBackfill();

// Tabs
$$('.tab').forEach(t=>t.addEventListener('click',()=>{
  $$('.tab').forEach(t2=>t2.classList.remove('active'));
  t.classList.add('active');
  currentTab=t.dataset.tab;
  if(currentTab==='recent') loadRecent();
  else if(currentTab==='leaderboard') loadLeaderboard();
  else if(currentTab==='showbill') showShowBill();
  else $('#content').innerHTML='<div class="empty">Search for an artist above</div>';
  if(window.innerWidth<=768) $('#sidebar').classList.remove('open');
}));

// Search
$('#searchForm').addEventListener('submit',async e=>{
  e.preventDefault();
  const artist=$('#artist').value.trim();
  if(!artist) return;
  const days=getDays();
  const stations=getSelectedStations();
  $('#searchBtn').disabled=true;
  $('#content').innerHTML='<div class="status"><span class="spinner"></span>Searching...</div>';
  try{
    let url=`/api/search?artist=${encodeURIComponent(artist)}&days=${days}`;
    const yr2=getYearRange();
    if(stations.length) url+=stations.map(s=>`&station=${s}`).join('');
    if($('#localToggle').checked) url+='&local=1';
    if(yr2.year_min) url+=`&year_min=${yr2.year_min}`;
    if(yr2.year_max) url+=`&year_max=${yr2.year_max}`;
    const resp=await fetch(url);
    const data=await resp.json();
    if(data.error) throw new Error(data.error);
    renderResults(data,artist,days);
  }catch(err){
    $('#content').innerHTML=`<div class="status error">Error: ${err.message}</div>`;
  }
  $('#searchBtn').disabled=false;
});

function renderResults(data,artist,days){
  if(!data.results.length){
    $('#content').innerHTML=`<div class="empty">No plays found for "${esc(artist)}"</div>`;
    return;
  }
  const total=data.results.reduce((n,r)=>n+r.spins.length,0);
  let html=`<div class="status">Found ${total} play${total!==1?'s':''} across ${data.results.length} show${data.results.length!==1?'s':''}</div>`;
  html+='<div class="table-wrap"><table><thead><tr><th>Station</th><th>Date</th><th>Time</th><th class="hide-mobile">DJ</th><th class="hide-mobile">Show</th><th>Artist</th><th>Song</th><th class="hide-mobile">Album</th></tr></thead><tbody>';
  for(const r of data.results){
    for(const s of r.spins){
      html+=`<tr>
        <td><strong>${esc(r.station||'')}</strong></td>
        <td>${r.date||''}</td><td>${s.time}</td>
        <td class="dj-name hide-mobile">${esc(r.dj_name)}</td>
        <td class="hide-mobile"><a class="playlist-link" onclick="loadPlaylist(${r.playlist_id})">${esc(r.show_name)}</a></td>
        <td class="artist-name">${esc(s.artist)}${loc(s.local)}</td>
        <td class="song-name">${esc(s.song)}${yr(s.year)}${mlinks(s.artist,s.song)}</td>
        <td class="meta wrap hide-mobile">${esc(s.album)}</td></tr>`;
    }
  }
  html+='</tbody></table></div>';
  $('#content').innerHTML=html;
}

async function loadRecent(){
  $('#content').innerHTML='<div class="status"><span class="spinner"></span>Loading...</div>';
  try{
    const resp=await fetch('/api/recent');
    const data=await resp.json();
    let html='<div class="table-wrap"><table><thead><tr><th>Station</th><th>Time</th><th>Show</th><th>DJ</th></tr></thead><tbody>';
    for(const r of data){
      html+=`<tr><td><strong>${esc(r.station||'')}</strong></td><td>${r.time}</td>
        <td><a class="playlist-link" onclick="loadPlaylist(${r.id})">${esc(r.show)}</a></td>
        <td class="dj-name">${esc(r.dj)}</td></tr>`;
    }
    html+='</tbody></table></div>';
    $('#content').innerHTML=html;
  }catch(err){$('#content').innerHTML=`<div class="status error">Error: ${err.message}</div>`}
}

async function loadLeaderboard(){
  const days=getDays();
  const stations=getSelectedStations();
  const genres=getSelectedGenres();
  $('#content').innerHTML='<div class="status"><span class="spinner"></span>Loading top artists...</div>';
  try{
    const yr=getYearRange();
    let url=`/api/top-artists?days=${days}`;
    if(stations.length) url+=stations.map(s=>`&station=${s}`).join('');
    if(genres.length) url+=genres.map(g=>`&tag=${encodeURIComponent(g)}`).join('');
    if($('#localToggle').checked) url+='&local=1';
    if(yr.year_min) url+=`&year_min=${yr.year_min}`;
    if(yr.year_max) url+=`&year_max=${yr.year_max}`;
    const resp=await fetch(url);
    const data=await resp.json();
    if(!data.length){$('#content').innerHTML='<div class="empty">No data for these filters</div>';return}
    let html='<div class="table-wrap"><table><thead><tr><th>#</th><th>Artist</th><th>Plays</th><th>Shows</th><th>Stations</th></tr></thead><tbody>';
    data.forEach((a,i)=>{
      html+=`<tr style="cursor:pointer" data-artist="${esc(a.artist).replace(/"/g,'&quot;')}" onclick="searchArtist(this.dataset.artist,event)">
        <td class="rank">${i+1}</td><td class="artist-name">${esc(a.artist)}${loc(a.local)}${mlinks(a.artist)}</td>
        <td class="plays">${a.plays}</td><td class="plays">${a.shows}</td>
        <td><div class="station-tags">${a.stations.map(s=>`<span class="station-tag">${esc(s)}</span>`).join('')}</div></td></tr>`;
    });
    html+='</tbody></table></div>';
    $('#content').innerHTML=html;
  }catch(err){$('#content').innerHTML=`<div class="status error">Error: ${err.message}</div>`}
}

function showShowBill(){
  let html=`<div class="showbill-header">Find local Bay Area bands for a show bill. Enter a band name to find who fits.</div>`;
  html+=`<div class="showbill-input"><input type="text" id="showbillArtist" placeholder="Your band name..." value="The Lenticular Clouds"><button onclick="loadShowBill()">Find Bands</button></div>`;
  html+=`<div id="showbillResults"></div>
  <div id="showbillPitch" style="margin-top:1.5rem"></div>`;
  $('#content').innerHTML=html;
  loadShowBill();
}

async function loadShowBill(){
  const artist=$('#showbillArtist')?.value?.trim();
  if(!artist) return;
  const el=$('#showbillResults');
  el.innerHTML='<div class="status"><span class="spinner"></span>Finding bands...</div>';
  try{
    const resp=await fetch(`/api/show-bill?artist=${encodeURIComponent(artist)}`);
    const data=await resp.json();
    if(!data.length){el.innerHTML='<div class="empty">No recommendations found. Try a different artist or check back as more data loads.</div>';return}
    let html='<div class="table-wrap"><table><thead><tr><th>#</th><th>Band</th><th>City</th><th>Why</th><th>Release</th></tr></thead><tbody>';
    data.forEach((r,i)=>{
      const signals=[];
      if(r.venue_confirmed) signals.push('plays Bottom of the Hill');
      if(r.seed_variety>0) signals.push(`paired with ${r.seed_variety} similar artists`);
      if(r.genre_match>0) signals.push(`${r.genre_match} genre overlap`);
      const badges=loc(true)+(r.venue_confirmed?'<span class="venue-badge">BOTH</span>':'');
      html+=`<tr>
        <td class="rank">${i+1}</td>
        <td class="artist-name">${esc(r.artist)}${badges}${mlinks(r.artist)}</td>
        <td class="rec-city">${esc(r.city)}</td>
        <td class="rec-signals">${signals.join(' · ')}</td>
        <td>${r.newest_release||'?'}</td>
      </tr>`;
    });
    html+='</tbody></table></div>';
    el.innerHTML=html;
    // Generate bill proposals
    const pitch=$('#showbillPitch');
    if(data.length>=2){
      const shoegaze=data.filter(r=>r.genre_match>=4).slice(0,2);
      const artsy=data.filter(r=>r.seed_variety>=3).slice(0,2);
      const venue=data.filter(r=>r.venue_confirmed).slice(0,2);
      let ph='<div style="margin-top:1rem"><div class="filter-title" style="font-size:.8rem;margin-bottom:.8rem">Suggested Bills</div>';
      const bills=[];
      if(venue.length) bills.push({name:'Venue-Tested',acts:venue,note:'These bands already play Bottom of the Hill'});
      if(shoegaze.length>=2) bills.push({name:'Genre Night',acts:shoegaze,note:'Strongest genre overlap'});
      if(artsy.length>=2) bills.push({name:'DJ Picks',acts:artsy,note:'Paired together most by local DJs'});
      bills.forEach(b=>{
        ph+=`<div style="background:#332060;border:1px solid #5a3d7a;border-radius:6px;padding:.8rem;margin-bottom:.6rem">`;
        ph+=`<div style="color:#e060a0;font-weight:600;font-size:.85rem;margin-bottom:.4rem">${b.name}</div>`;
        ph+=`<div style="color:#e8e0f0;font-size:.9rem">${esc(artist)}</div>`;
        b.acts.forEach(a=>ph+=`<div style="color:#c8a0c8;font-size:.85rem">+ ${esc(a.artist)} <span style="color:#7a6090;font-size:.75rem">${esc(a.city)}</span></div>`);
        ph+=`<div style="color:#7a6090;font-size:.7rem;margin-top:.3rem">${b.note}</div></div>`;
      });
      ph+='</div>';
      pitch.innerHTML=ph;
    }
  }catch(err){el.innerHTML=`<div class="status error">Error: ${err.message}</div>`}
}

function searchArtist(name,e){
  if(e&&e.target.closest('.music-links')) return;
  $('#artist').value=name;
  $$('.tab').forEach(t=>t.classList.remove('active'));
  $$('.tab')[0].classList.add('active');
  currentTab='results';
  $('#searchForm').dispatchEvent(new Event('submit'));
}

async function loadPlaylist(id){
  $('#content').innerHTML='<div class="status"><span class="spinner"></span>Loading playlist...</div>';
  try{
    const resp=await fetch(`/api/playlist/${id}`);
    const data=await resp.json();
    if(data.error) throw new Error(data.error);
    let html=`<div class="back-link" onclick="goBack()">&larr; Back</div>`;
    html+=`<div class="playlist-header"><h2>${esc(data.show_name)}</h2>`;
    html+=`<div class="details"><span class="dj-name">${esc(data.dj_name)}</span> &middot; ${esc(data.date_str)}</div></div>`;
    if(!data.spins.length){html+='<div class="empty">No spins logged</div>'}
    else{
      html+='<div class="table-wrap"><table><thead><tr><th>Time</th><th>Artist</th><th>Song</th><th>Album</th><th>Label</th></tr></thead><tbody>';
      for(const s of data.spins){
        html+=`<tr><td>${s.time}</td><td class="artist-name">${esc(s.artist)}${mlinks(s.artist,s.song)}</td>
          <td class="song-name">${esc(s.song)}${yr(s.year)}</td><td class="meta wrap">${esc(s.album)}</td>
          <td class="meta">${esc(s.label)}</td></tr>`;
      }
      html+='</tbody></table></div>';
    }
    $('#content').innerHTML=html;
  }catch(err){$('#content').innerHTML=`<div class="status error">Error: ${err.message}</div>`}
}

function goBack(){
  if(currentTab==='recent') loadRecent();
  else if(currentTab==='leaderboard') loadLeaderboard();
  else $('#content').innerHTML='<div class="empty">Search for an artist above</div>';
}

function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
function loc(isLocal){return isLocal?'<span class="local-badge">BAY AREA</span>':''}
function yr(y){return y?`<span class="year-tag">${y}</span>`:''}
function mlinks(artist,song){
  const q=encodeURIComponent(song?artist+' '+song:artist);
  return `<span class="music-links">`
    +`<a href="https://open.spotify.com/search/${q}" target="_blank" rel="noopener">spotify</a>`
    +`<span class="sep"> · </span>`
    +`<a href="https://music.apple.com/us/search?term=${q}" target="_blank" rel="noopener">apple</a>`
    +`<span class="sep"> · </span>`
    +`<a href="https://bandcamp.com/search?q=${q}" target="_blank" rel="noopener">bandcamp</a>`
    +`<span class="sep"> · </span>`
    +`<a href="https://tidal.com/search?q=${q}" target="_blank" rel="noopener">tidal</a>`
    +`</span>`;
}

// Load leaderboard on startup
fetch('/api/stats').then(r=>r.json()).then(data=>{
  if(!data.playlists){
    $('#content').innerHTML='<div class="empty">Data is loading in the background. Refresh in a minute.</div>';
  } else {
    loadLeaderboard();
  }
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/search")
def api_search():
    artist = request.args.get("artist", "").strip()
    days = int(request.args.get("days", 7))
    stations_list = [s for s in request.args.getlist("station") if s.strip()]
    local_only = request.args.get("local") == "1"
    year_min = int(request.args["year_min"]) if request.args.get("year_min") else None
    year_max = int(request.args["year_max"]) if request.args.get("year_max") else None
    if not artist:
        return jsonify({"error": "No artist specified"}), 400

    start_date = (datetime.now() - timedelta(days=days)).date()
    end_date = datetime.now().date()
    stations = stations_list or None

    conn = get_connection()
    results = search_db(conn, artist, start_date, end_date, stations=stations, local_only=local_only, year_min=year_min, year_max=year_max)
    conn.close()

    return jsonify({
        "results": [
            {
                "playlist_id": r["playlist_id"],
                "station": r.get("station", "KALX"),
                "show_name": r["show_name"],
                "dj_name": r["dj_name"],
                "date": r["date"].strftime("%a %m/%d") if r["date"] else "",
                "spins": r["spins"],
            }
            for r in results
        ],
    })


@app.route("/api/top-artists")
def api_top_artists():
    days = int(request.args.get("days", 7))
    stations_list = [s for s in request.args.getlist("station") if s.strip()]
    tags_list = [t for t in request.args.getlist("tag") if t.strip()]
    local_only = request.args.get("local") == "1"
    year_min = int(request.args["year_min"]) if request.args.get("year_min") else None
    year_max = int(request.args["year_max"]) if request.args.get("year_max") else None
    limit = int(request.args.get("limit", 50))

    start_date = (datetime.now() - timedelta(days=days)).date()
    end_date = datetime.now().date()
    stations = stations_list or None

    conn = get_connection()
    results = get_top_artists(conn, start_date, end_date, stations=stations, tags=tags_list or None, local_only=local_only, year_min=year_min, year_max=year_max, limit=limit)
    conn.close()
    return jsonify(results)


@app.route("/api/tags")
def api_tags():
    conn = get_connection()
    tags = get_all_tags(conn)
    conn.close()
    return jsonify(tags)


@app.route("/api/show-bill")
def api_show_bill():
    artist = request.args.get("artist", "").strip()
    if not artist:
        return jsonify({"error": "No artist specified"}), 400
    from recommend import recommend_show_bill
    conn = get_connection()
    results = recommend_show_bill(conn, artist)
    conn.close()
    return jsonify(results)


@app.route("/api/stats")
def api_stats():
    conn = get_connection()
    stats = get_db_stats(conn)
    conn.close()
    return jsonify(stats)


@app.route("/api/backfill-status")
def api_backfill_status():
    from db import DB_PATH
    status_file = DB_PATH.parent / "backfill_status.json"
    if status_file.exists():
        return jsonify(json.loads(status_file.read_text()))
    return jsonify({"running": False, "phase": "unknown"})


@app.route("/api/recent")
def api_recent():
    from bs4 import BeautifulSoup
    import re

    conn = get_connection()
    db_stations = get_db_stats(conn)["stations"]
    conn.close()

    items = []
    for station in (db_stations or ["KALX"]):
        html = fetch(f"{SPINITRON_BASE}/{station}/")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        recent = soup.find("div", class_="recent-playlists")
        if not recent:
            continue
        for row in recent.find_all("tr"):
            time_cell = row.find("td", class_="show-time")
            pl_link = row.find("a", href=re.compile(rf"/{station}/pl/\d+"))
            if not pl_link:
                continue
            match = re.search(r"/\w+/pl/(\d+)", pl_link["href"])
            dj_link = row.find("a", href=re.compile(rf"/{station}/dj/"))
            items.append({
                "station": station,
                "time": time_cell.get_text(strip=True) if time_cell else "",
                "show": pl_link.get_text(strip=True),
                "id": int(match.group(1)) if match else 0,
                "dj": dj_link.get_text(strip=True) if dj_link else "",
            })
    return jsonify(items)


@app.route("/api/playlist/<int:playlist_id>")
def api_playlist(playlist_id):
    conn = get_connection()
    playlist = get_playlist_from_db(conn, playlist_id)
    conn.close()

    if not playlist:
        playlist = fetch_playlist(playlist_id)

    if not playlist:
        return jsonify({"error": "Playlist not found"}), 404
    return jsonify({
        "show_name": playlist["show_name"],
        "dj_name": playlist["dj_name"],
        "date_str": playlist["date_str"],
        "spins": playlist["spins"],
    })


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = not os.environ.get("RENDER")
    print(f"Starting Bay Area Radio Play Log at http://localhost:{port}")
    app.run(debug=debug, host="0.0.0.0", port=port)
