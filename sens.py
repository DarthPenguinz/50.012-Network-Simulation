from manifest import *
from functions import *

if __name__ == '__main__':
    sens_id = sys.argv[1]
    sens_id = int(sens_id)
    sleep_time = sys.argv[2]
    sleep_time = int(sleep_time)
    print("SENSOR ID: ", sens_id)
    
    
    init_list = []
    for idx in sensor_cluster_link[sens_id]:
        init_list.append((idx, cluster_heads[idx][0], cluster_heads[idx][1]))
    sensor = Sensor(sens_id, init_list, 10)
    counter = 0
    time.sleep(10)
    while True:
        time.sleep(sleep_time)
        counter += 1
        fields = sensors_types[sens_id]
        data_field = {}
        priority = random.choice([True, False])
        for field in fields:
            data_field[field] = random.randint(0, 100)
        data = DataPacket(sensor.id, priority, data_field, counter)
        msg, pkt_no = data.get_data()
        sensor.send_data(msg, pkt_no)
