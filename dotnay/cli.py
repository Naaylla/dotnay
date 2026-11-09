import sys

from .parser import NaylaError, load_nayla


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python -m dotnay.cli FILE.nayla")
        return 2

    try:
        document = load_nayla(args[0])
    except NaylaError as exc:
        print(f"Invalid .nayla file: {exc}")
        return 1

    if document.is_expired():
        status = "expired"
    else:
        status = f"{document.remaining()} left"

    expires = document.expires_at.isoformat(sep=" ", timespec="seconds")
    print(f"Expires: {expires} ({status})")
    print("---")
    print(document.content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
