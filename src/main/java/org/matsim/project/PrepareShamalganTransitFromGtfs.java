package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.NetworkWriter;
import org.matsim.contrib.gtfs.GtfsConverter;
import org.matsim.contrib.gtfs.RunGTFS2MATSim;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.pt.transitSchedule.api.TransitScheduleWriter;
import org.matsim.vehicles.MatsimVehicleWriter;

import java.time.LocalDate;

/**
 * Converts a GTFS feed into MATSim transit schedule + vehicles and augments
 * the road network with a pseudo transit network.
 */
public final class PrepareShamalganTransitFromGtfs {

	private static final String TARGET_CRS = "EPSG:32643";

	private PrepareShamalganTransitFromGtfs() {
	}

	public static void main(String[] args) {
		if (args.length < 6) {
			System.err.println("Usage:");
			System.err.println("  PrepareShamalganTransitFromGtfs "
				+ "<gtfs.zip> <inputNetwork.xml> <outputNetwork.xml> "
				+ "<outputTransitSchedule.xml> <outputTransitVehicles.xml> "
				+ "<serviceDate(yyyy-mm-dd)> [mergeStopsMode] [useExtendedRouteTypes]");
			System.err.println("mergeStopsMode options: doNotMerge | mergeStopsAtSameCoord | "
				+ "mergeToGtfsParentStation | mergeToParentAndRouteTypes");
			System.exit(1);
		}

		String gtfsZip = args[0];
		String inputNetwork = args[1];
		String outputNetwork = args[2];
		String outputTransitSchedule = args[3];
		String outputTransitVehicles = args[4];
		LocalDate serviceDate = LocalDate.parse(args[5]);

		GtfsConverter.MergeGtfsStops mergeStops = args.length >= 7
			? GtfsConverter.MergeGtfsStops.valueOf(args[6])
			: GtfsConverter.MergeGtfsStops.mergeStopsAtSameCoord;
		boolean useExtendedRouteTypes = args.length >= 8 && Boolean.parseBoolean(args[7]);

		Config config = ConfigUtils.createConfig();
		config.global().setCoordinateSystem(TARGET_CRS);
		config.network().setInputFile(inputNetwork);
		config.transit().setUseTransit(true);
		Scenario scenario = ScenarioUtils.loadScenario(config);

		CoordinateTransformation transformation =
			TransformationFactory.getCoordinateTransformation(TransformationFactory.WGS84, TARGET_CRS);

		RunGTFS2MATSim.convertGTFSandAddToScenario(
			scenario,
			gtfsZip,
			serviceDate,
			serviceDate,
			transformation,
			true,
			true,
			useExtendedRouteTypes,
			mergeStops
		);

		new NetworkWriter(scenario.getNetwork()).write(outputNetwork);
		new TransitScheduleWriter(scenario.getTransitSchedule()).writeFile(outputTransitSchedule);
		new MatsimVehicleWriter(scenario.getTransitVehicles()).writeFile(outputTransitVehicles);

		System.out.println("GTFS conversion completed.");
		System.out.println("Network: " + outputNetwork);
		System.out.println("Transit schedule: " + outputTransitSchedule);
		System.out.println("Transit vehicles: " + outputTransitVehicles);
	}
}
