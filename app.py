#!/usr/bin/env python3
"""Show Bill — find Bay Area bands to play with."""

import json
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template_string, request

from db import get_connection, get_db_stats
from recommend import recommend_show_bill

app = Flask(__name__)

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Show Bill</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#241848;color:#e8e0f0;min-height:100vh}

.hero{text-align:center;padding:3rem 1.5rem 2rem}
.hero h1{font-size:2rem;font-weight:800;letter-spacing:-.03em;margin-bottom:.4rem}
.hero h1 span{color:#e060a0}
.hero p{color:#9a80b0;font-size:1rem;max-width:500px;margin:0 auto}

.search-area{max-width:520px;margin:0 auto 2rem;padding:0 1.5rem}
.search-box{display:flex;gap:.5rem}
.search-box input{flex:1;background:#332060;border:1px solid #5a3d7a;border-radius:8px;color:#e8e0f0;padding:.7rem 1rem;font-size:1rem}
.search-box input:focus{outline:none;border-color:#e060a0}
.search-box input::placeholder{color:#7a6090}
.search-box button{background:#e060a0;color:#fff;border:none;border-radius:8px;padding:.7rem 1.5rem;font-size:1rem;font-weight:600;cursor:pointer;white-space:nowrap}
.search-box button:hover{background:#c84888}
.search-box button:disabled{background:#5a3d7a;color:#7a6090;cursor:wait}

.results{max-width:700px;margin:0 auto;padding:0 1.5rem 3rem}

.status{color:#9a80b0;font-size:.85rem;padding:.5rem 0;text-align:center}
.status.error{color:#e88080}
.empty{color:#7a6090;padding:2rem;text-align:center}

.spinner{display:inline-block;width:14px;height:14px;border:2px solid #5a3d7a;border-top-color:#e060a0;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:.4rem}
@keyframes spin{to{transform:rotate(360deg)}}

/* Band cards */
.band-card{background:#2d1a50;border:1px solid #4a3870;border-radius:10px;padding:1rem 1.2rem;margin-bottom:.8rem;transition:border-color .15s}
.band-card:hover{border-color:#5a3d7a}
.band-top{display:flex;align-items:baseline;gap:.5rem;margin-bottom:.3rem;flex-wrap:wrap}
.band-name{font-size:1.1rem;font-weight:700;color:#e8e0f0}
.band-city{color:#9a80b0;font-size:.8rem}
.band-badges{display:flex;gap:.3rem;flex-wrap:wrap}
.badge{font-size:.65rem;padding:.15rem .4rem;border-radius:3px;font-weight:600;letter-spacing:.02em}
.badge-venue{background:#4a3870;color:#c8a0c8}
.badge-active{background:#3a5a35;color:#a0d89a}
.band-why{color:#9a80b0;font-size:.8rem;margin-bottom:.5rem;line-height:1.4}
.band-links{display:flex;gap:.8rem;font-size:.78rem}
.band-links a{color:#7a6090;text-decoration:none;transition:color .15s}
.band-links a:hover{color:#e060a0}

/* Suggested bills */
.bills-section{margin-top:2rem}
.bills-title{font-size:.75rem;color:#7a6090;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.8rem;text-align:center}
.bill{background:#332060;border:1px solid #5a3d7a;border-radius:8px;padding:1rem;margin-bottom:.6rem}
.bill-theme{color:#e060a0;font-weight:600;font-size:.85rem;margin-bottom:.5rem}
.bill-lineup{color:#c8a0c8;font-size:.9rem;line-height:1.6}
.bill-lineup .you{color:#e8e0f0;font-weight:600}
.bill-note{color:#7a6090;font-size:.7rem;margin-top:.3rem}

/* Artist detail */
.back-link{color:#9a80b0;cursor:pointer;font-size:.85rem;margin-bottom:1rem;display:inline-block}
.back-link:hover{color:#e060a0}
.detail-header{margin-bottom:1rem}
.detail-header h2{font-size:1.3rem;margin-bottom:.2rem}
.detail-header p{color:#9a80b0;font-size:.85rem}
.tracks-list{list-style:none}
.tracks-list li{padding:.4rem 0;border-bottom:1px solid #332060;display:flex;justify-content:space-between;align-items:center}
.track-name{color:#e8e0f0;font-size:.85rem}
.track-meta{color:#7a6090;font-size:.75rem}
.track-links{font-size:.7rem}
.track-links a{color:#7a6090;text-decoration:none;margin-left:.5rem}
.track-links a:hover{color:#e060a0}

.footer{text-align:center;padding:2rem;color:#5a3d7a;font-size:.7rem}

@media(max-width:600px){
  .hero{padding:2rem 1rem 1.5rem}
  .hero h1{font-size:1.5rem}
  .hero p{font-size:.85rem}
  .search-area{padding:0 1rem}
  .search-box input{font-size:16px}
  .search-box{flex-wrap:wrap}
  .search-box button{width:100%}
  .results{padding:0 1rem 2rem}
  .band-card{padding:.8rem 1rem}
}
</style>
</head>
<body>

<div class="hero">
  <h1><span>Show Bill</span></h1>
  <p>Find Bay Area bands to play with. Enter your band and we'll find who fits.</p>
</div>

<div class="search-area">
  <form id="searchForm" class="search-box">
    <input type="text" id="bandInput" placeholder="Your band name..." value="The Lenticular Clouds" autofocus>
    <button type="submit" id="goBtn">Find Bands</button>
  </form>
</div>

<div class="results" id="results"></div>

<div class="footer">
  Built from 6 months of Bay Area radio data, Bandcamp recommendations, venue lineups, and genre analysis.
</div>

<script>
const $=s=>document.querySelector(s);

$('#searchForm').addEventListener('submit',async e=>{
  e.preventDefault();
  const band=$('#bandInput').value.trim();
  if(!band) return;
  $('#goBtn').disabled=true;
  $('#results').innerHTML='<div class="status"><span class="spinner"></span>Searching...</div>';
  try{
    const resp=await fetch(`/api/recommend?artist=${encodeURIComponent(band)}`);
    const data=await resp.json();
    if(data.error) throw new Error(data.error);
    renderResults(data,band);
  }catch(err){
    $('#results').innerHTML=`<div class="status error">${err.message}</div>`;
  }
  $('#goBtn').disabled=false;
});

function renderResults(data,band){
  if(!data.recommendations.length){
    $('#results').innerHTML='<div class="empty">No recommendations found. Try a different band name, or check back as more data loads.</div>';
    return;
  }

  let html='';

  // Explanation blurb
  const nRecs=data.recommendations.length;
  const hasVenue=data.recommendations.some(r=>r.venue_confirmed);
  html+=`<div style="text-align:center;color:#9a80b0;font-size:.8rem;margin-bottom:1.5rem;line-height:1.5">
    Found <strong style="color:#e8e0f0">${nRecs} local bands</strong> that fit with <strong style="color:#e060a0">${esc(band)}</strong>.<br>
    Based on Bay Area radio playlists, genre analysis, ${hasVenue?'venue lineups, ':''}and scene connections.
  </div>`;

  // Build specific bill suggestions from tag data
  const recs=data.recommendations;
  const hasTags=(r,list)=>(r.tags||[]).some(t=>list.includes(t));
  const gaze=recs.filter(r=>hasTags(r,['shoegaze','dream pop','noise pop','space rock']));
  const psych=recs.filter(r=>hasTags(r,['psychedelic rock','psychedelic','psych rock','garage rock']));
  const punk=recs.filter(r=>hasTags(r,['post-punk','new wave','dark wave']));
  const folk=recs.filter(r=>hasTags(r,['folk','singer-songwriter','freak folk','lo-fi']));
  const venue=recs.filter(r=>r.venue_confirmed);

  const bills=[];
  if(gaze.length>=2) bills.push({theme:'Shoegaze Night',acts:gaze.slice(0,2),note:'Wall of sound, heads down, pedals on'});
  if(psych.length>=2) bills.push({theme:'Psych Rock Triple Bill',acts:psych.slice(0,2),note:'Cosmic vibes, long jams, third eyes open'});
  if(venue.length) bills.push({theme:'Venue-Tested',acts:venue.slice(0,2),note:'Already confirmed at Bottom of the Hill'});
  if(punk.length>=2 && bills.length<3) bills.push({theme:'Post-Punk Night',acts:punk.slice(0,2),note:'Angular guitars, driving bass, art damage'});
  if(folk.length>=2 && bills.length<3) bills.push({theme:'Quiet Storm',acts:folk.slice(0,2),note:'Stripped back, intimate, songwriter-focused'});

  if(bills.length){
    html+='<div class="bills-section"><div class="bills-title">Suggested lineups</div>';
    bills.slice(0,3).forEach(b=>{
      html+=`<div class="bill"><div class="bill-theme">${esc(b.theme)}</div><div class="bill-lineup">`;
      html+=`<div class="you">${esc(band)}</div>`;
      b.acts.forEach(a=>{html+=`<div>+ ${esc(a.artist)} <span style="color:#7a6090;font-size:.8rem">${esc(a.city)}</span></div>`});
      html+=`</div><div class="bill-note">${b.note}</div></div>`;
    });
    html+='</div>';
  }

  // Band cards
  html+=`<div style="margin-top:1.5rem">`;
  data.recommendations.forEach((r,i)=>{
    const badges=[];
    if(r.venue_confirmed) badges.push('<span class="badge badge-venue">PLAYS BOTTOM OF THE HILL</span>');
    if(r.newest_release && r.newest_release>=2025) badges.push(`<span class="badge badge-active">NEW RELEASE ${r.newest_release}</span>`);

    const q=encodeURIComponent(r.artist);
    const tagHtml=(r.tags||[]).map(t=>`<span style="color:#9a80b0;font-size:.7rem;background:#332060;padding:.1rem .35rem;border-radius:3px">${esc(t)}</span>`).join(' ');

    html+=`<div class="band-card" id="card-${i}">
      <div class="band-top" style="cursor:pointer" data-artist="${esc(r.artist).replace(/"/g,'&quot;')}" data-idx="${i}" onclick="toggleDetail(this.dataset.artist,this.dataset.idx)">
        <span class="band-name">${esc(r.artist)}</span>
        ${r.city?`<span class="band-city">${esc(r.city)}</span>`:''}
        <div class="band-badges">${badges.join('')}</div>
      </div>
      ${tagHtml?`<div style="display:flex;gap:.3rem;flex-wrap:wrap;margin:.3rem 0">${tagHtml}</div>`:''}
      <div class="band-links">
        <a href="https://bandcamp.com/search?q=${q}" target="_blank">bandcamp</a>
        <a href="https://open.spotify.com/search/${q}" target="_blank">spotify</a>
        <a href="https://music.apple.com/us/search?term=${q}" target="_blank">apple music</a>
      </div>
      <div class="band-detail" id="detail-${i}" style="display:none"></div>
    </div>`;
  });
  html+=`</div>`;
  $('#results').innerHTML=html;
}

async function toggleDetail(artist,idx){
  const el=$(`#detail-${idx}`);
  if(el.style.display!=='none'){el.style.display='none';return}
  el.style.display='block';
  if(el.dataset.loaded){return}
  el.innerHTML='<div class="status"><span class="spinner"></span></div>';
  try{
    const resp=await fetch(`/api/artist-detail?artist=${encodeURIComponent(artist)}`);
    const data=await resp.json();
    let html='';
    if(data.tracks.length){
      html+='<ul class="tracks-list" style="margin-top:.5rem">';
      data.tracks.slice(0,8).forEach(t=>{
        const q=encodeURIComponent(data.artist+' '+t.song);
        html+=`<li><span class="track-name">${esc(t.song)}</span>
          <span class="track-meta">${esc(t.album)}${t.year?' ('+t.year+')':''}
            <span class="track-links">
              <a href="https://open.spotify.com/search/${q}" target="_blank">spotify</a>
              <a href="https://bandcamp.com/search?q=${q}" target="_blank">bandcamp</a>
            </span></span></li>`;
      });
      html+='</ul>';
    }else{html='<div style="color:#7a6090;font-size:.8rem;padding:.5rem 0">No tracks found on Bay Area radio</div>'}
    el.innerHTML=html;
    el.dataset.loaded='1';
  }catch(err){el.innerHTML=`<div class="status error">${err.message}</div>`}
}

function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}

// Auto-search on load
$('#searchForm').dispatchEvent(new Event('submit'));
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/recommend")
def api_recommend():
    artist = request.args.get("artist", "").strip()
    if not artist:
        return jsonify({"error": "Enter a band name"}), 400

    conn = get_connection()
    recs = recommend_show_bill(conn, artist, limit=20)

    conn.close()
    return jsonify({"recommendations": recs})


@app.route("/api/artist-detail")
def api_artist_detail():
    artist = request.args.get("artist", "").strip()
    if not artist:
        return jsonify({"error": "No artist"}), 400

    conn = get_connection()
    tracks = conn.execute("""
        SELECT s.song, s.album, COUNT(*) as plays,
               GROUP_CONCAT(DISTINCT p.station) as stations,
               ay.release_year
        FROM spins s
        JOIN playlists p ON s.playlist_id = p.playlist_id
        LEFT JOIN album_years ay ON s.artist = ay.artist COLLATE NOCASE AND s.album = ay.album COLLATE NOCASE
        WHERE s.artist = ? COLLATE NOCASE
        GROUP BY s.song COLLATE NOCASE, s.album COLLATE NOCASE
        ORDER BY plays DESC
        LIMIT 15
    """, (artist,)).fetchall()

    loc = conn.execute(
        "SELECT begin_area FROM artist_locations WHERE artist = ? COLLATE NOCASE",
        (artist,)
    ).fetchone()

    newest = conn.execute(
        "SELECT MAX(release_year) FROM album_years WHERE artist = ? COLLATE NOCASE AND release_year > 0",
        (artist,)
    ).fetchone()

    conn.close()
    return jsonify({
        "artist": artist,
        "city": loc[0] if loc else "",
        "newest_release": newest[0] if newest and newest[0] else None,
        "tracks": [
            {"song": t[0], "album": t[1], "plays": t[2],
             "stations": t[3].split(",") if t[3] else [],
             "year": t[4] if t[4] and t[4] > 0 else None}
            for t in tracks
        ],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = not os.environ.get("RENDER")
    print(f"Show Bill running at http://localhost:{port}")
    app.run(debug=debug, host="0.0.0.0", port=port)
