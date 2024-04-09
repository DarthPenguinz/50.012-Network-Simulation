from manifest import cluster_heads
from functions import * 


if __name__ == '__main__':
    interval = sys.argv[1]
    interval = float(interval)
    buffersize = sys.argv[2]
    buffersize = int(buffersize)
    
    print("MAIN SERVER")
    ClusterHead1 = MainServer(main_server[0], main_server[1], id = 1, buffer_size = buffersize, send_interval=interval) 
    ClusterHead1.start_server()
    
