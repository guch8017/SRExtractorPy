import logging

base_name = 'SRExtractor'
base_logger = logging.getLogger(base_name)
base_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s: %(message)s',
                              '%Y-%m-%d %H:%M:%S')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
base_logger.addHandler(handler)


def get_logger(name: str):
    return logging.getLogger(base_name + '.' + name)
