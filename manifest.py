main_server = ("127.0.0.1", 56788)

cluster_heads = {
    1: ("127.0.0.1", 12345),
    2: ("127.0.0.1", 12346),
    3: ("127.0.0.1", 12347)
}

sensors_types = {
    1: ["temperature", "humidity"],
    2: ["temperature", "humidity", "light"],
    3: ["heat", "fire", "ph"],
}


sensor_cluster_link = {
    1: [1, 2],
    2: [1, 2],
    3: [1, 2]
}

sensor_timeout = {
    1: 10,
    2: 10,
    3: 10
}

