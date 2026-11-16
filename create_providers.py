import os
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-this-key"),
    MYSQL_HOST=os.getenv("MYSQL_HOST", "localhost"),
    MYSQL_USER=os.getenv("MYSQL_USER", "root"),
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", ""),
    MYSQL_DB=os.getenv("MYSQL_DB", "homeease"),
    MYSQL_CURSORCLASS="DictCursor",
)

mysql = MySQL(app)
bcrypt = Bcrypt(app)


def create_provider_account():
    with app.app_context():
        cur = mysql.connection.cursor()

        try:
            cur.execute(
                "SELECT id, name, phone FROM providers WHERE active = 1 ORDER BY id"
            )
            providers = cur.fetchall()

            if not providers:
                print("No active providers found.")
                return

            print("\n=== HomeEase Provider Accounts ===")

            for provider in providers:
                print(
                    f"\nProvider: {provider['name']} "
                    f"(ID: {provider['id']}, Phone: {provider['phone']})"
                )

                cur.execute(
                    "SELECT user_id FROM providers WHERE id = %s",
                    (provider["id"],),
                )
                linked = cur.fetchone()

                if linked["user_id"]:
                    print("An account is already linked. Skipping.")
                    continue

                email = input("Enter provider login email: ").strip().lower()

                if "@" not in email:
                    print("Invalid email. Skipping this provider.")
                    continue

                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    print("This email already exists. Choose another email.")
                    continue

                password = input("Set a password (at least 8 characters): ")
                confirm = input("Enter the password again: ")

                if len(password) < 8 or password != confirm:
                    print("Passwords do not match or are too short. Skipping.")
                    continue

                password_hash = bcrypt.generate_password_hash(
                    password
                ).decode("utf-8")

                cur.execute(
                    """
                    INSERT INTO users (name, email, password_hash, phone, role)
                    VALUES (%s, %s, %s, %s, 'provider')
                    """,
                    (
                        provider["name"],
                        email,
                        password_hash,
                        provider["phone"],
                    ),
                )

                user_id = cur.lastrowid

                cur.execute(
                    "UPDATE providers SET user_id = %s WHERE id = %s",
                    (user_id, provider["id"]),
                )

                mysql.connection.commit()
                print("Provider account created successfully!")

        except Exception:
            mysql.connection.rollback()
            raise
        finally:
            cur.close()


if __name__ == "__main__":
    create_provider_account()