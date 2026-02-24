package org.matsim.project;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.Leg;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Population;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.config.groups.PlansConfigGroup;
import org.matsim.core.population.PopulationUtils;
import org.matsim.core.scenario.ScenarioUtils;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Creates a simple synthetic population for Shamalgan.
 *
 * This is a starter generator: it builds home-work-home and home-other-home plans.
 * You can calibrate all important variables in the USER SETTINGS section below.
 */
public class PrepareShamalganPopulation {

	// =========================
	// USER SETTINGS (edit here)
	// =========================
	private static final int AGENT_COUNT = 5000;
	private static final double EMPLOYED_SHARE = 0.65;
	private static final double CAR_MODE_SHARE = 0.55;
	private static final double PT_MODE_SHARE = 0.25;
	// Remaining share goes to walk (1 - CAR_MODE_SHARE - PT_MODE_SHARE)
	private static final double MIN_HOME_WORK_DISTANCE_METERS = 1500.0;
	private static final double MAX_HOME_WORK_DISTANCE_METERS = 35000.0;
	private static final double WORK_START_MEAN_SECONDS = 8.0 * 3600.0;
	private static final double WORK_START_STD_SECONDS = 45.0 * 60.0;
	private static final long RANDOM_SEED = 20260217L;

	public static void main(String[] args) throws Exception {
		if (args.length < 2) {
			System.out.println("Usage:");
			System.out.println("  PrepareShamalganPopulation <input-network.xml> <output-population.xml>");
			System.out.println("Example:");
			System.out.println("  PrepareShamalganPopulation scenarios/shamalgan/network.xml scenarios/shamalgan/population.xml");
			return;
		}

		String networkFile = args[0];
		String populationOut = args[1];
		Path networkPath = Path.of(networkFile);
		if (!Files.exists(networkPath)) {
			throw new IllegalArgumentException("Network file not found: " + networkPath.toAbsolutePath());
		}

		Config config = ConfigUtils.createConfig();
		config.network().setInputFile(networkPath.toString());

		// Keep only selected plan for each person in output plans file.
		config.plans().setRemovingUnneccessaryPlanAttributes(true);
		config.plans().setActivityDurationInterpretation(PlansConfigGroup.ActivityDurationInterpretation.minOfDurationAndEndTime);

		Scenario scenario = ScenarioUtils.loadScenario(config);
		Population population = scenario.getPopulation();
		Network network = scenario.getNetwork();

		List<Link> candidateLinks = new ArrayList<>();
		for (Link link : network.getLinks().values()) {
			if (link.getAllowedModes().contains(TransportMode.car) && link.getLength() > 10) {
				candidateLinks.add(link);
			}
		}

		if (candidateLinks.isEmpty()) {
			throw new IllegalStateException("No usable car links found in network. Check network input.");
		}

		SplittableRandom rnd = new SplittableRandom(RANDOM_SEED);
		for (int i = 0; i < AGENT_COUNT; i++) {
			Person person = population.getFactory().createPerson(Id.createPersonId("shamalgan_" + i));
			Plan plan = population.getFactory().createPlan();

			Link homeLink = pickRandom(candidateLinks, rnd);
			boolean employed = rnd.nextDouble() < EMPLOYED_SHARE;
			String mainMode = drawMode(rnd);

			if (employed) {
				Link workLink = pickWorkLink(homeLink, candidateLinks, rnd);
				buildHomeWorkHomePlan(plan, homeLink, workLink, mainMode, rnd);
			} else {
				Link otherLink = pickWorkLink(homeLink, candidateLinks, rnd);
				buildHomeOtherHomePlan(plan, homeLink, otherLink, mainMode, rnd);
			}

			person.addPlan(plan);
			population.addPerson(person);
		}

		Path out = Path.of(populationOut);
		if (out.getParent() != null) {
			Files.createDirectories(out.getParent());
		}

		PopulationUtils.writePopulation(population, out.toString());
		System.out.println("Population created: " + out.toAbsolutePath() + " (agents=" + AGENT_COUNT + ")");
	}

	private static void buildHomeWorkHomePlan(Plan plan, Link home, Link work, String mode, SplittableRandom rnd) {
		double workStart = clamp(gaussianApprox(rnd, WORK_START_MEAN_SECONDS, WORK_START_STD_SECONDS), 6 * 3600.0, 11 * 3600.0);
		double workDuration = clamp(gaussianApprox(rnd, 8.5 * 3600.0, 1.0 * 3600.0), 5 * 3600.0, 11 * 3600.0);

		Activity home1 = PopulationUtils.createActivityFromLinkId("home", home.getId());
		home1.setEndTime(workStart - travelTimeGuess(mode, home, work));
		Leg leg1 = PopulationUtils.createLeg(mode);
		Activity workAct = PopulationUtils.createActivityFromLinkId("work", work.getId());
		workAct.setEndTime(workStart + workDuration);
		Leg leg2 = PopulationUtils.createLeg(mode);
		Activity home2 = PopulationUtils.createActivityFromLinkId("home", home.getId());

		plan.addActivity(home1);
		plan.addLeg(leg1);
		plan.addActivity(workAct);
		plan.addLeg(leg2);
		plan.addActivity(home2);
	}

	private static void buildHomeOtherHomePlan(Plan plan, Link home, Link other, String mode, SplittableRandom rnd) {
		double otherStart = clamp(gaussianApprox(rnd, 12.0 * 3600.0, 2.0 * 3600.0), 8.0 * 3600.0, 18.0 * 3600.0);
		double otherDuration = clamp(gaussianApprox(rnd, 2.0 * 3600.0, 1.0 * 3600.0), 0.5 * 3600.0, 6.0 * 3600.0);

		Activity home1 = PopulationUtils.createActivityFromLinkId("home", home.getId());
		home1.setEndTime(otherStart - travelTimeGuess(mode, home, other));
		Leg leg1 = PopulationUtils.createLeg(mode);
		Activity otherAct = PopulationUtils.createActivityFromLinkId("other", other.getId());
		otherAct.setEndTime(otherStart + otherDuration);
		Leg leg2 = PopulationUtils.createLeg(mode);
		Activity home2 = PopulationUtils.createActivityFromLinkId("home", home.getId());

		plan.addActivity(home1);
		plan.addLeg(leg1);
		plan.addActivity(otherAct);
		plan.addLeg(leg2);
		plan.addActivity(home2);
	}

	private static String drawMode(SplittableRandom rnd) {
		double x = rnd.nextDouble();
		if (x < CAR_MODE_SHARE) {
			return TransportMode.car;
		}
		if (x < CAR_MODE_SHARE + PT_MODE_SHARE) {
			return TransportMode.pt;
		}
		return TransportMode.walk;
	}

	private static Link pickWorkLink(Link home, List<Link> links, SplittableRandom rnd) {
		for (int tries = 0; tries < 250; tries++) {
			Link candidate = pickRandom(links, rnd);
			double distance = distance(home, candidate);
			if (distance >= MIN_HOME_WORK_DISTANCE_METERS && distance <= MAX_HOME_WORK_DISTANCE_METERS) {
				return candidate;
			}
		}
		return pickRandom(links, rnd);
	}

	private static Link pickRandom(List<Link> links, SplittableRandom rnd) {
		return links.get(rnd.nextInt(links.size()));
	}

	private static double distance(Link a, Link b) {
		double dx = a.getCoord().getX() - b.getCoord().getX();
		double dy = a.getCoord().getY() - b.getCoord().getY();
		return Math.hypot(dx, dy);
	}

	private static double travelTimeGuess(String mode, Link from, Link to) {
		double distance = Math.max(500.0, distance(from, to));
		double speed;
		switch (mode) {
			case TransportMode.car -> speed = 13.0;
			case TransportMode.pt -> speed = 7.5;
			default -> speed = 1.3;
		}
		return distance / speed;
	}

	private static double gaussianApprox(SplittableRandom rnd, double mean, double std) {
		// Approximate normal distribution by summing uniforms (CLT).
		double sum = 0;
		for (int i = 0; i < 12; i++) {
			sum += rnd.nextDouble();
		}
		double z = sum - 6.0;
		return mean + z * std;
	}

	private static double clamp(double value, double min, double max) {
		return Math.max(min, Math.min(max, value));
	}
}
