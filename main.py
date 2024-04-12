from config import cluster_heads
from functions import * 


if __name__ == '__main__':
    interval = sys.argv[1]
    interval = float(interval)
    buffersize = sys.argv[2]
    buffersize = int(buffersize)
    use_priority = "True"
    try:
        use_priority = sys.argv[3]
    except:
        pass
    if use_priority == "False":
        use_priority = False
    else:
        use_priority = True
    
    print("MAIN SERVER")
    print(use_priority)
    ClusterHead1 = MainServer(main_server[0], main_server[1], id = 1, buffer_size = buffersize, send_interval=interval, use_priority_queue=use_priority) 
    ClusterHead1.start_server()
    
