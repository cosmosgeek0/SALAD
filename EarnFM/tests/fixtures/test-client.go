package main
import("net";"fmt";"time";"os")
func main(){
 c,e:=net.Dial("tcp","127.0.0.1:8443");if e!=nil{panic(e)}
 if os.Getenv("EF_CASE")=="startup_burst" { c.Write(make([]byte,2<<20));time.Sleep(time.Hour);return }
 for i:=0;i<4;i++{fmt.Println("WebSocket DNS lookup failed for primary.earn.fm: timeout");time.Sleep(time.Second)}
 c.Close();time.Sleep(2*time.Second)
 c,e=net.Dial("tcp","127.0.0.1:8443");if e!=nil{panic(e)}
 defer c.Close();time.Sleep(time.Hour)
}
