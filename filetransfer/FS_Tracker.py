from filetransfer.tracker import Tracker


def main():
    tracker = Tracker()
    try:
        tracker.start()
    except KeyboardInterrupt:
        pass
    finally:
        tracker.close()


if __name__ == "__main__":
    main()
