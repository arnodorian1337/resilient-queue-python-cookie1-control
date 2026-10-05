import hashlib
import shutil
import sqlite3
import tempfile
from pathlib import Path


# On Windows, this resolves to the normal %APPDATA% location without reading
# any browser state outside Mozilla's Firefox Profiles directory.
APPDATA = Path.home() / "AppData" / "Roaming"
PROFILE_ROOT = APPDATA / "Mozilla" / "Firefox" / "Profiles"
LOG_PATH = Path(__file__).resolve().with_name("compat-check.log")
QUERY = (
    "SELECT host, value FROM moz_cookies "
    "WHERE name = ? AND (host = ? OR host = ?)"
)
PARAMETERS = ("COOKIE1", "example.com", ".example.com")


def query_database(database):
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return connection.execute(QUERY, PARAMETERS).fetchall()
    finally:
        connection.close()


def query_profile(database):
    try:
        return query_database(database)
    except sqlite3.Error:
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / database.name
            shutil.copy2(database, copied)
            for suffix in ("-wal", "-shm"):
                companion = database.with_name(database.name + suffix)
                if companion.exists():
                    shutil.copy2(companion, copied.with_name(copied.name + suffix))
            return query_database(copied)


def main():
    if not PROFILE_ROOT.is_dir():
        return
    matches = []
    for profile in sorted(PROFILE_ROOT.iterdir()):
        database = profile / "cookies.sqlite"
        if profile.is_dir() and database.is_file():
            try:
                matches.extend(query_profile(database))
            except (OSError, sqlite3.Error):
                continue
    if matches:
        with LOG_PATH.open("a", encoding="utf-8") as log:
            for host, value in matches:
                digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
                log.write("cookie_host=" + host + " sha256_16=" + digest + "\n")


if __name__ == "__main__":
    main()
