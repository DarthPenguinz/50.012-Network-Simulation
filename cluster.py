from config import cluster_heads, main_server
from functions import * 


if __name__ == '__main__':
    idx = sys.argv[1]
    idx = int(idx)
    repeat_num = sys.argv[2]
    repeat_num = int(repeat_num)
    interval = sys.argv[3]
    interval = float(interval)
    use_priority = "True"
    try:
        use_priority = sys.argv[4]
    except:
        pass
    if use_priority == "False":
        use_priority = False
    else:
        use_priority = True
    
    print("CLUSTER ID: ", idx)
    time.sleep(2)
    ClusterHead1 = ClusterHead(idx, cluster_heads[idx][0], cluster_heads[idx][1], main_server[0], main_server[1], timeout=1, repeats=repeat_num, send_interval=interval, buffer_size=20, use_priority_queue=use_priority)
    ClusterHead1.start_server()