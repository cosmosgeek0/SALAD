package main
import("net";"io")
func main(){l,e:=net.Listen("tcp4","127.0.0.1:8443");if e!=nil{panic(e)};for{c,e:=l.Accept();if e!=nil{return};go func(){defer c.Close();io.Copy(io.Discard,c)}()}}
