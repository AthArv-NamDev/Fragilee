// The model knows these 15 countries. Any other country is grouped as "other" by the API.
export const COUNTRY_NAMES: Record<string, string> = {
  USA: "United States", GBR: "United Kingdom", CAN: "Canada", ISR: "Israel", RUS: "Russia",
  FRA: "France", DEU: "Germany", CHN: "China", IND: "India", ESP: "Spain", AUS: "Australia",
  SWE: "Sweden", BRA: "Brazil", NLD: "Netherlands", IRL: "Ireland",
};
// Sent when the founder picks "Somewhere else". It is not a real country code, so the API groups it as other.
export const OTHER_COUNTRY = "OTH";

export const US_STATES: [string, string][] = [
  ["AL","Alabama"],["AK","Alaska"],["AZ","Arizona"],["AR","Arkansas"],["CA","California"],["CO","Colorado"],
  ["CT","Connecticut"],["DE","Delaware"],["DC","District of Columbia"],["FL","Florida"],["GA","Georgia"],
  ["HI","Hawaii"],["ID","Idaho"],["IL","Illinois"],["IN","Indiana"],["IA","Iowa"],["KS","Kansas"],
  ["KY","Kentucky"],["LA","Louisiana"],["ME","Maine"],["MD","Maryland"],["MA","Massachusetts"],
  ["MI","Michigan"],["MN","Minnesota"],["MS","Mississippi"],["MO","Missouri"],["MT","Montana"],
  ["NE","Nebraska"],["NV","Nevada"],["NH","New Hampshire"],["NJ","New Jersey"],["NM","New Mexico"],
  ["NY","New York"],["NC","North Carolina"],["ND","North Dakota"],["OH","Ohio"],["OK","Oklahoma"],
  ["OR","Oregon"],["PA","Pennsylvania"],["RI","Rhode Island"],["SC","South Carolina"],["SD","South Dakota"],
  ["TN","Tennessee"],["TX","Texas"],["UT","Utah"],["VT","Vermont"],["VA","Virginia"],["WA","Washington"],
  ["WV","West Virginia"],["WI","Wisconsin"],["WY","Wyoming"],
];
export const STATE_NAMES: Record<string, string> = Object.fromEntries(US_STATES);
