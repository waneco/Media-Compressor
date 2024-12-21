"""
ログ管理ツール

このスクリプトは、ログファイルの生成、圧縮、削除を自動化するためのツールです。
特に長期間運用されるアプリケーションやシステムで、ログファイルの肥大化を防ぎ、
効率的な管理を実現することを目的としています。

主な機能:
1. ログファイルの生成:
   - 標準フォーマットでのログ出力を行い、必要に応じてコンソールにも出力。
   - ログファイルは日付と時刻で命名され、階層を指定して保存先を柔軟に管理可能。

2. 古いファイルの圧縮:
   - 7日以上前の未圧縮ファイルを自動的に gzip 圧縮し、ディスク使用量を削減。

3. 古いファイルの削除:
   - 保存期間（デフォルト180日）を超えたファイルを自動的に削除し、ログディレクトリをクリーンに保つ。

4. ログローテーション:
   - ログファイルのサイズが一定以上になるとローテーションを行い、最大バックアップ世代数を維持。

使用方法:
- コマンドライン引数でログレベルや保存階層を指定可能。
- プログラム開始時に自動的にログ設定が初期化され、必要に応じて圧縮や削除を実行。

引数:
- --log-level: ログ出力のレベルを指定 (DEBUG, INFO, WARNING, ERROR, CRITICAL)。
- --levels-up: ログフォルダを作成する親ディレクトリまでの階層を指定。
"""

# 標準ライブラリ
import gzip
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

# 設定値
MAX_LEVELS_UP = 10  # ログフォルダ作成の際、親ディレクトリに遡る最大階層数
LOG_FOLDER_NAME = "logs"  # ログフォルダ作成の際、ログフォルダの名前
MAX_LOG_SIZE = 5 * 1024 * 1024  # ログファイルの最大サイズ (5MB)
BACKUP_COUNT = 30  # ログファイルのバックアップ世代数
LOG_RETENTION_DAYS = 180  # 保存期間 (180日以上前のファイルを削除)
COMPRESS_DAYS = 7  # 圧縮するファイルの基準日（7日前より古いファイルを圧縮）
TARGET_FILE_EXTENSIONS = [".log", ".csv"]  # 圧縮・削除対象のファイル拡張子


def compress_old_log(file_path: Path) -> None:
    """
    指定されたファイルを gzip 圧縮します。
    既に圧縮済みのファイルや存在しないファイルはスキップします。
    """
    if not file_path.exists() or file_path.suffix == ".gz":
        return
    try:
        with open(file_path, "rb") as f_in:
            with gzip.open(f"{file_path}.gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        file_path.unlink()  # 元ファイルを削除
    except Exception as e:
        print(f"[ERROR] 圧縮エラー: {file_path} - {e}")


def compress_logs_older_than(log_dir: Path, cutoff_days: int, logger: logging.Logger) -> None:
    """
    指定された日数より古い未圧縮ファイルを圧縮します。
    対象: 設定された拡張子のファイル
    """
    cutoff_date = datetime.now() - timedelta(days=cutoff_days)
    for file in log_dir.glob("*"):
        if file.suffix not in TARGET_FILE_EXTENSIONS:
            continue
        try:
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if file_mtime < cutoff_date:
                logger.info(f"{cutoff_days}日前の未圧縮ファイルを圧縮開始: {file}")
                compress_old_log(file)
                logger.info(f"{cutoff_days}日前の未圧縮ファイルを圧縮完了: {file}")
        except Exception as e:
            logger.error(f"[ERROR] ファイルの圧縮中にエラー: {file} - {e}")


def delete_old_logs(log_dir: Path, retention_days: int, logger: logging.Logger) -> None:
    """
    指定された保存期間を超えた古いファイルを削除します。
    対象: 圧縮済みファイルと設定された拡張子のファイル
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    for file in log_dir.glob("*"):
        if file.suffix not in TARGET_FILE_EXTENSIONS + [".gz"]:
            continue
        try:
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if file_mtime < cutoff_date:
                logger.info(f"{retention_days}日前の古いファイルを削除開始: {file}")
                file.unlink()
                logger.info(f"{retention_days}日前の古いファイルを削除完了: {file}")
        except Exception as e:
            logger.error(f"[ERROR] ファイルの削除中にエラー: {file} - {e}")


def setup_log_directory(levels_up: int) -> Path:
    """
    ログディレクトリを設定し、パスを返します。
    """
    if levels_up == 0:
        # 現在のスクリプトのディレクトリにログフォルダを作成
        log_dir = Path(__file__).resolve().parent / LOG_FOLDER_NAME
    else:
        # 指定された階層に基づいてログフォルダを作成
        log_dir = Path(__file__).resolve().parents[levels_up] / LOG_FOLDER_NAME

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def create_log_file_path(log_dir: Path, logger_name: str) -> Path:
    """
    ログファイルのパスを生成して返します。
    """
    now = datetime.now() #+ timedelta(hours=9)  # UTC+9 (日本時間)
    return log_dir / f"{now.strftime('%Y%m%d_%H%M%S')}_{logger_name}.log"


def initialize_logger(logger_name: str, log_level: str, log_file: Path) -> logging.Logger:
    """
    ロガーを初期化して返します。
    """
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    return logger


def setup_logging(logger_name: str = "applicationLogger", levels_up: int = 1, log_level: str = "DEBUG") -> tuple:
    """
    ログの設定を行い、ロガーとログファイルパスを返します。
    """
    log_dir = setup_log_directory(levels_up)
    log_file = create_log_file_path(log_dir, logger_name)
    logger = initialize_logger(logger_name, log_level, log_file)

    # 古いログの管理 (圧縮と削除)＊正常なLOG書き出しが確認出来てから上から順番にコメントアウトしたほうが安全です
    # compress_logs_older_than(log_dir, cutoff_days=COMPRESS_DAYS, logger=logger)
    # delete_old_logs(log_dir, retention_days=LOG_RETENTION_DAYS, logger=logger)

    logger.info(f"ロギング設定が完了しました。ログファイル: {log_file}")
    return logger, log_file


def parse_arguments():
    """
    コマンドライン引数を解析します。
    """
    parser = argparse.ArgumentParser(description="Logging Setup")
    parser.add_argument(
        "--log-level",
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="ログレベルを指定します (デフォルト: DEBUG)",
    )
    parser.add_argument(
        "--levels-up",
        type=int,
        default=1,
        help=f"ログフォルダを作成する階層の深さ (0 以上 {MAX_LEVELS_UP} 以下, デフォルト: 1)",
    )
    args = parser.parse_args()

    # levels_up の値を検証
    if args.levels_up < 0 or args.levels_up > MAX_LEVELS_UP:
        parser.error(f"--levels-up は 0 以上 {MAX_LEVELS_UP} 以下で指定してください。")

    return args


if __name__ == "__main__":
    args = parse_arguments()
    logger, log_path = setup_logging(logger_name="customLogger", levels_up=args.levels_up, log_level=args.log_level)

    # テスト用ログメッセージを出力
    logger.debug("デバッグメッセージ")
    logger.info("情報メッセージ")
    logger.warning("警告メッセージ")
    logger.error("エラーメッセージ")
    logger.critical("重大メッセージ")

    print(f"ログファイルのパス: {log_path}")
