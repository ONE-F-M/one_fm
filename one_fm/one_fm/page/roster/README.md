# Roster

Roster DocType is a Job Assigning Platform where we can Assign Employees on a daily Basis
[Roster Dev OneFM](https://dev.one-fm.com/desk#roster)


1. We can Assign the Staffs (Rostering)
2. View all Staffs (Staff)
3. View Reports and Statistics (Reports) 

## Main Functions

```javascript
load_js(page){
//Initializes the page with default values
...}
bind_events(page) {
//Bind events to Edit options in Roster/Post view
...}
GetHeaders (IsMonthSet, element) {
// function for dynamic set calender header data on right calender
...}
```

## Rostering Functions

```javascript
get_roster_data(page, isOt) {
// Get data for Roster monthly view and render it
// isOt Parms is passed for Roster OT
...}
get_roster_week_data(page, isOt) {
// Get data for Roster weekly view and render it
...}
get_post_data(page) {
// Get data for Post view monthly and render it
...}
get_post_week_data(page) {
// Get data for Post view monthly and render it
...}
```

## Staff Functions

```javascript
staffmanagement() {
//datatable function call for staff
...}
```

## Contributing
Open a new Branch and Open a PR to Master

Please make sure to test.
