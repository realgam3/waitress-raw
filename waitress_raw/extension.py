def process(log):
    log["request"] = repr(log["request"])
    log["body"] = repr(log["body"])
    return log
