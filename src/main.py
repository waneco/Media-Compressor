# メディアファイルを圧縮・リサイズしつつ、タイムスタンプやメタデータ（EXIF情報など）を保持するプログラム
# 主な機能:
# - 対応する画像や動画をリサイズして圧縮
# - メタデータ（撮影日時や場所情報など）を保持
# - タイムスタンプ（作成日時、変更日時）を保持
# - RAW画像（.arw, .nef）およびHEIC画像（.heic）にも対応
# - 未対応のファイルはスキップ

import os
import shutil
import rawpy
from PIL import Image
from PIL.Image import Resampling  # Resamplingを明示的に指定
import pillow_heif
import ffmpeg
from log_setting import setup_logging

# ロガーのセットアップ
logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger, log_path = setup_logging(logger_name=logger_name, levels_up=0, log_level='DEBUG')

# このスクリプトが存在するフォルダのパスを取得
script_dir = os.path.dirname(os.path.abspath(__file__))

# 入力フォルダと出力フォルダを設定
SOURCE_DIR = os.path.join(script_dir, "Input")  # 元データフォルダ
OUTPUT_DIR = os.path.join(script_dir, "Output")  # 出力フォルダ

# 入力フォルダと出力フォルダを直接指定する場合は下記２行をコメントアウト
#SOURCE_DIR = r'G:\photo\01_photo(sync)'
#OUTPUT_DIR = r'D:\photo'

# 必要なフォルダを作成
os.makedirs(SOURCE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# フルHDのサイズ制限
MAX_SIZE = 1920

# 動画圧縮設定
VIDEO_CONFIG = {
    "vcodec": "libx264",
    "crf": 23,
    "preset": "medium",
    "acodec": "aac",
    "movflags": "use_metadata_tags"
}

# 出力先フォルダのパスを生成
def get_output_path(input_path: str, extension: str = None, include_original_ext: bool = False) -> str:
    """
    入力ファイルのパスを基に出力先パスを生成し、フォルダを作成する。

    Args:
        input_path (str): 入力ファイルのフルパス。
        extension (str): 出力ファイルの拡張子（例: ".jpg"）。
        include_original_ext (bool): 元の拡張子をファイル名に含めるか。

    Returns:
        str: 出力先ファイルのフルパス。
    """
    relative_path = os.path.relpath(input_path, SOURCE_DIR)
    base, original_ext = os.path.splitext(relative_path)
    if extension:
        if include_original_ext:
            relative_path = f"{base}_{original_ext[1:]}{extension}"  # 元の拡張子を含む
        else:
            relative_path = f"{base}{extension}"
    output_path = os.path.join(OUTPUT_DIR, relative_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    return output_path

# 動画の解像度を取得
def get_video_resolution(input_path: str) -> tuple:
    """
    動画の幅と高さを取得。

    Args:
        input_path (str): 入力動画ファイルのフルパス。

    Returns:
        tuple: (幅, 高さ) を含むタプル。取得できない場合は (None, None)。
    """
    try:
        probe = ffmpeg.probe(input_path)
        video_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']
        if video_streams:
            width = int(video_streams[0]['width'])
            height = int(video_streams[0]['height'])
            return width, height
    except Exception as e:
        logger.error(f"解像度取得エラー: {input_path}, エラー内容: {e}")
    return None, None

import subprocess

def compress_videos(input_path: str, output_path: str) -> None:
    """
    動画を指定された設定で圧縮し、必要に応じて解像度を縮小。

    Args:
        input_path (str): 入力動画ファイルのフルパス。
        output_path (str): 出力動画ファイルのフルパス。

    Returns:
        None
    """
    try:
        width, height = get_video_resolution(input_path)

        # 解像度取得失敗時は元の解像度で圧縮
        if width is None or height is None:
            logger.warning(f"解像度が取得できないため、元の解像度で圧縮: {input_path}")
            ffmpeg.input(input_path).output(
                output_path,
                **VIDEO_CONFIG
            ).run(overwrite_output=True)
            shutil.copystat(input_path, output_path)
            logger.info(f"動画を圧縮（解像度変更なし）: {output_path}")
            return

        # 縦横いずれかが1920を超える場合は縮小
        if width > MAX_SIZE or height > MAX_SIZE:
            scale_filter = f"scale='if(gt(iw,ih),{MAX_SIZE},-2):if(gt(ih,iw),{MAX_SIZE},-2):force_original_aspect_ratio=decrease'"
            ffmpeg.input(input_path).output(
                output_path,
                vf=scale_filter,
                **VIDEO_CONFIG
            ).run(overwrite_output=True)
            logger.info(f"動画を縮小して圧縮: {output_path}")
        else:
            # 解像度が1920以下の場合はそのまま圧縮
            ffmpeg.input(input_path).output(
                output_path,
                **VIDEO_CONFIG
            ).run(overwrite_output=True)
            logger.info(f"動画を圧縮: {output_path}")

        shutil.copystat(input_path, output_path)

    except ffmpeg.Error as e:
        stderr_output = e.stderr.decode("utf-8") if e.stderr else "No stderr output"
        logger.error(f"動画処理エラー: {input_path}, エラー内容: {stderr_output}")


# 画像のリサイズ
def resize_image(img: Image.Image) -> Image.Image:
    """
    画像のサイズが制限を超えている場合、アスペクト比を維持して縮小。

    Args:
        img (Image.Image): PIL.Image オブジェクト。

    Returns:
        Image.Image: リサイズ後の PIL.Image オブジェクト。
    """
    width, height = img.size
    if width > MAX_SIZE or height > MAX_SIZE:
        if width > height:
            new_width = MAX_SIZE
            new_height = int(height * (MAX_SIZE / width))
        else:
            new_width = int(width * (MAX_SIZE / height))
            new_height = MAX_SIZE
        img = img.resize((new_width, new_height), Resampling.LANCZOS)
        logger.info(f"画像を縮小: {new_width}x{new_height}")
    return img

# 画像をリサイズして保存
def save_image_with_resize(img: Image.Image, input_path: str, output_path: str) -> None:
    """
    画像をリサイズしてJPEG形式で保存（EXIF情報を維持）。

    Args:
        img (Image.Image): PIL.Image オブジェクト。
        input_path (str): 入力画像ファイルのフルパス。
        output_path (str): 出力画像ファイルのフルパス。

    Returns:
        None
    """
    try:
        # 元画像のEXIF情報を取得（存在しない場合は None）
        exif_data = img.info.get("exif", None)

        # サイズ変更
        img = resize_image(img)

        # EXIF情報を維持して保存（EXIFが存在する場合のみ）
        if exif_data:
            img.save(output_path, "JPEG", quality=75, exif=exif_data)
        else:
            img.save(output_path, "JPEG", quality=75)

        shutil.copystat(input_path, output_path)
        logger.info(f"画像保存完了: {output_path}")
    except Exception as e:
        logger.error(f"画像保存エラー: {input_path}, エラー内容: {e}")

# 通常の写真の処理（JPEG/PNG/TIFF/WebP/BMPなど）
def compress_photos(input_path: str, output_path: str) -> None:
    """
    写真（JPEG/PNG/TIFF/WebP/BMPなど）をリサイズして保存。

    Args:
        input_path (str): 入力画像ファイルのフルパス。
        output_path (str): 出力画像ファイルのフルパス。

    Returns:
        None
    """
    try:
        img = Image.open(input_path)
        save_image_with_resize(img, input_path, output_path)
    except (IOError, OSError) as e:
        logger.error(f"画像ファイルが破損しているか不正です: {input_path}, エラー内容: {e}")
    except Exception as e:
        logger.error(f"写真処理エラー: {input_path}, エラー内容: {e}")

# RAW画像の処理（.arw, .nefなど）
def compress_raw(input_path: str, output_path: str) -> None:
    """
    RAW画像をリサイズしてJPEG形式で保存。

    Args:
        input_path (str): 入力RAW画像ファイルのフルパス。
        output_path (str): 出力画像ファイルのフルパス。

    Returns:
        None
    """
    try:
        with rawpy.imread(input_path) as raw:
            rgb = raw.postprocess()
            img = Image.fromarray(rgb)
            save_image_with_resize(img, input_path, output_path)
    except Exception as e:
        logger.error(f"RAW画像処理エラー: {input_path}, エラー内容: {e}")

from PIL import Image
import pillow_heif

# HEIC/HEIF形式をサポートするために登録
pillow_heif.register_heif_opener()

# HEIC画像の処理
def compress_heic(input_path: str, output_path: str) -> None:
    """
    HEIC画像をリサイズしてJPEG形式で保存。

    Args:
        input_path (str): 入力HEIC画像ファイルのフルパス。
        output_path (str): 出力画像ファイルのフルパス。

    Returns:
        None
    """
    try:
        img = Image.open(input_path)  # HEICを開く
        save_image_with_resize(img, input_path, output_path)
    except Exception as e:
        logger.error(f"HEIC画像処理エラー: {input_path}, エラー内容: {e}")

# メディアの処理
def process_media() -> None:
    """
    入力フォルダ内のすべてのメディアを処理。

    Args:
        None

    Returns:
        None
    """
    if not os.listdir(SOURCE_DIR):
        logger.warning("入力フォルダが空です。処理を終了します。")
        return

    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            input_path = os.path.join(root, file)
            file_lower = file.lower()

            # 出力パスの生成
            if file_lower.endswith(('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.mts')):
                output_path = get_output_path(input_path)
                if os.path.exists(output_path):
                    logger.info(f"スキップ: {output_path}（既に存在します）")
                    continue
                compress_videos(input_path, output_path)
            elif file_lower.endswith(('.jpg', '.jpeg', '.png', '.tiff', '.webp', '.bmp')):
                output_path = get_output_path(input_path, ".jpg")
                if os.path.exists(output_path):
                    logger.info(f"スキップ: {output_path}（既に存在します）")
                    continue
                compress_photos(input_path, output_path)
            elif file_lower.endswith(('.arw', '.nef')):
                output_path = get_output_path(input_path, ".jpg")
                if os.path.exists(output_path):
                    logger.info(f"スキップ: {output_path}（既に存在します）")
                    continue
                compress_raw(input_path, output_path)
            elif file_lower.endswith('.heic'):
                output_path = get_output_path(input_path, ".jpg")
                if os.path.exists(output_path):
                    logger.info(f"スキップ: {output_path}（既に存在します）")
                    continue
                compress_heic(input_path, output_path)
            else:
                logger.info(f"スキップ: {input_path}（未対応のファイル形式）")

if __name__ == "__main__":
    logger.info("メディア圧縮処理を開始します...")
    try:
        process_media()
    except Exception as e:
        logger.critical(f"重大なエラーが発生しました: {e}")
    logger.info(f"メディア圧縮処理が完了しました。ログは以下に記録されています: {log_path}")
