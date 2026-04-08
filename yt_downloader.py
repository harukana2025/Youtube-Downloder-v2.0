import streamlit as st
import yt_dlp
import os
import json
import datetime
import re

# Configure page
st.set_page_config(page_title="YouTube Web Downloader", page_icon="🎥", layout="wide")

# Custom CSS for aesthetics
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0d0e15 0%, #1a1c29 100%);
        color: #e0e0e0;
    }
    .stButton>button {
        background: linear-gradient(90deg, #ff416c 0%, #ff4b2b 100%);
        color: white;
        border: none;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(255, 65, 108, 0.4);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 65, 108, 0.6);
    }
    h1 {
        font-family: 'Inter', sans-serif;
        text-align: center;
        background: -webkit-linear-gradient(#90caf9, #f48fb1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# Define directories
DOWNLOAD_DIR = "downloads"
HISTORY_FILE = "history.json"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# History functions
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_history(title, link, format_type):
    history = load_history()
    history.insert(0, {
        "title": title,
        "url": link,
        "format": format_type,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

# Clean ANSI escape sequences from strings
def clean_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Sidebar (History)
with st.sidebar:
    st.header("🕒 ダウンロード履歴")
    history_data = load_history()
    if history_data:
        if st.button("履歴をクリア"):
            clear_history()
            st.rerun()
        for item in history_data[:10]: # show latest 10
            st.markdown(f"**{item['title']}**<br><small>{item['date']} | {item['format']}</small><br>[🔗 動画リンク]({item['url']})", unsafe_allow_html=True)
            st.divider()
    else:
        st.write("履歴はありません。")

st.title("🎥 YouTube Downloader")
st.markdown("<p style='text-align: center; color: #b0bec5;'>Download high quality video or audio directly.</p>", unsafe_allow_html=True)

# Inputs
url = st.text_input("🔗 Enter YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")
format_choice = st.selectbox("📂 Select Format:", ["Video (Highest Quality)", "Audio Only (MP3)"])

def get_info(url):
    ydl_opts = {'quiet': True, 'skip_download': True, 'ffmpeg_location': './ffmpeg' if os.path.exists('./ffmpeg') else 'ffmpeg'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        return None

if url:
    with st.spinner("Fetching video info..."):
        info = get_info(url)
        
    if info:
        st.success("Information fetched successfully!")
        
        # Display Info
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(info.get('thumbnail', ''), use_container_width=True)
        with col2:
            st.subheader(info.get('title', 'Unknown Title'))
            duration = info.get('duration', 0)
            st.write(f"**Duration:** {duration // 60}m {duration % 60}s")
            st.write(f"**Channel:** {info.get('uploader', 'Unknown')}")
            
        
        if "download_path" not in st.session_state:
            st.session_state.download_path = None
        if "download_format" not in st.session_state:
            st.session_state.download_format = None

        if st.button("🚀 Start Download"):
            # Progress placeholders
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_hook(d):
                if d['status'] == 'downloading':
                    try:
                        p_str = d.get('_percent_str', '0.0%').strip()
                        p_str_clean = clean_ansi(p_str)
                        p_clean = p_str_clean.replace('%', '')
                        if p_clean != 'Unknown':
                            percent = float(p_clean) / 100.0
                            progress_bar.progress(percent)
                        status_text.text(f"Downloading... {p_str_clean} | Speed: {clean_ansi(d.get('_speed_str', ''))} | ETA: {clean_ansi(d.get('_eta_str', ''))}")
                    except BaseException:
                        pass
                elif d['status'] == 'processing':
                    status_text.text("Processing media files (merging/extracting)...")
                elif d['status'] == 'finished':
                    progress_bar.progress(1.0)
                    status_text.text("Download complete! Processing final file...")

            # Base options
            ydl_opts = {
                'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'ffmpeg_location': './ffmpeg' if os.path.exists('./ffmpeg') else 'ffmpeg',
                'progress_hooks': [progress_hook],
            }
            
            if format_choice == "Audio Only (MP3)":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:  # Video
                ydl_opts.update({
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                })
                
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dl = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info_dl)
                    
                    if format_choice == "Audio Only (MP3)":
                        file_path = os.path.splitext(file_path)[0] + '.mp3'
                        
                st.success("🎉 Download Complete!")
                status_text.empty()
                progress_bar.empty()
                
                # Save History
                save_history(info_dl.get('title', 'Unknown Title'), url, format_choice)
                
                # Persist the file path to session state
                st.session_state.download_path = file_path
                st.session_state.download_format = format_choice

            except Exception as e:
                st.error(f"Error during download: {e}")

        # If a file was successfully downloaded recently, show the preview and download button
        if st.session_state.download_path and os.path.exists(st.session_state.download_path):
            file_path = st.session_state.download_path
            f_choice = st.session_state.download_format
            
            st.divider()
            st.subheader("▶️ Preview (ここですぐ再生！)")
            
            if "Audio" in f_choice:
                st.audio(file_path)
            else:
                st.video(file_path)

            st.info("💡 下のボタンを押すと、Chromebook本体 (chrome://downloads/) にファイルとして保存されます。")
            with open(file_path, "rb") as file:
                st.download_button(
                    label="💾 Chromebookに保存する (Save to PC)",
                    data=file,
                    file_name=os.path.basename(file_path),
                    mime="audio/mpeg" if "Audio" in f_choice else "video/mp4"
                )
    else:
        st.error("Could not fetch information. Please check if the URL is correct.")
