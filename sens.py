from config import *
from functions import *

if __name__ == '__main__':
    sens_id = sys.argv[1]
    sens_id = int(sens_id)
    interval = sys.argv[2]
    interval = float(interval)
    repeat_num = sys.argv[3]
    repeat_num = int(repeat_num)
    print("SENSOR ID: ", sens_id)
    
    
    init_list = []
    for idx in sensor_cluster_link[sens_id]:
        init_list.append((idx, cluster_heads[idx][0], cluster_heads[idx][1]))
    sensor = Sensor(sens_id, init_list, 1, repeats=repeat_num)
    counter = 0
    time.sleep(5)
    while True:
        time.sleep(interval)
        counter += 1
        fields = sensors_types[sens_id]
        data_field = {}
        priority = random.choice([True, False])
        for field in fields:
            data_field[field] = random.randint(0, 100)
        data = DataPacket(sensor.id, priority, data_field, counter)
        msg, pkt_no = data.get_data()
        sensor.send_data(msg, pkt_no, priority)
        if counter % 10 == 0:
            counter += 1
            # Add 1 as this packet also sent but not counted here. 
            total = sensor.total_sent
            for key in sensor.total_sent.keys():
                total[key] += 1
            metric = {"sent": total}
            new_data = DataPacket(sensor.id, False, metric, counter, metric=True)
            new_msg, new_pkt_no = new_data.get_data()
            sensor.send_data(new_msg, pkt_no=new_pkt_no, priority=False)
