// Runs the SHIPPED `const order = ...` line from _applyMerge against the object the
// solo branch builds by hand. A run of one card carries no itinerary, and dereferencing
// one threw before anything else in the method could run.
const merged = JSON.parse(process.argv[2]);
const order = (merged.itinerary || []).map((s) => s.shipment);
process.stdout.write(JSON.stringify(order));

