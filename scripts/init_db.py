from triage_iq.db.connection import engine
from triage_iq.db.models import Base


def main() -> None:
    url = engine.url.render_as_string(hide_password=True)
    print(f"Creating tables on {url} ...")

    Base.metadata.create_all(engine)

    print("Done. Tables present:")
    for table_name in Base.metadata.tables:
        print(f"  - {table_name}")


if __name__ == "__main__":
    main()
