package domain

type InventoryItem struct {
	ID string `json:"id"`
	Name string `json:"name"`
	Quantity int `json:"quantity"`
}
