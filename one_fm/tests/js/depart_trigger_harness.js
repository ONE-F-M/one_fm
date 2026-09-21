// Runs the SHIPPED canTrigger decision from renderDepartCard.
// Which camp may start a check is a position, not a seq - and seq is exactly the value
// that used to be mistaken for one, so this has to be executed rather than grepped.
const a = JSON.parse(process.argv[2]);
const isMixed = a.isMixed, activeStop = a.activeStop, campIndex = a.campIndex,
      activeIndex = a.activeIndex;
		const position = (campIndex === null || campIndex === undefined) ? null : campIndex;
		const nextToTrigger = activeStop
			? ((activeIndex === null || activeIndex === undefined || activeIndex < 0)
				? null : activeIndex + 1)
			: 0;
		const canTrigger = isMixed
			? (position === 0 && !activeStop)
			: (position !== null && position === nextToTrigger);
process.stdout.write(JSON.stringify({ canTrigger: canTrigger }));

