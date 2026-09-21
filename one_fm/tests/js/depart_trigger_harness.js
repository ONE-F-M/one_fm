// Runs the SHIPPED canTrigger decision from renderDepartCard.
const a = JSON.parse(process.argv[2]);
const isMixed = a.isMixed, activeStop = a.activeStop, campIndex = a.campIndex,
      activeIndex = a.activeIndex, isActive = a.isActive || false;
		const position = (campIndex === null || campIndex === undefined) ? null : campIndex;
		const canTrigger = position !== null && position === activeIndex && !isActive;
process.stdout.write(JSON.stringify({ canTrigger: canTrigger }));

