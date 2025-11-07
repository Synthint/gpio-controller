package main

import (
	"log"
	"time"

	"periph.io/x/conn/v3/gpio"
	host "periph.io/x/host/v3"
	"periph.io/x/host/v3/rpi"
)

func doGPIO() error {
	log.Printf("Loading periph.io drivers")
	// Load periph.io drivers:
	if _, err := host.Init(); err != nil {
		return err
	}
	log.Printf("Toggling GPIO forever")
	t := time.NewTicker(5 * time.Second)
	for l := gpio.Low; ; l = !l {
		log.Printf("setting GPIO pin number 18 (signal BCM24) to %v", l)
		// Lookup a pin by its location on the board:
		if err := rpi.P1_18.Out(l); err != nil {
			return err
		}
		<-t.C
	}
}

func main() {
	if err := doGPIO(); err != nil {
		log.Fatal(err)
	}
}